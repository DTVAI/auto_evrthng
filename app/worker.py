"""Durable local-only evaluation worker. Never performs external effects."""

import argparse
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, or_, and_
from sqlalchemy.exc import OperationalError
from .db import SessionLocal, init_db
from .models import Event, Job
from .services import evaluate, save_run

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
MAX_DB_FAILURES = 8
heartbeat = {"state": "starting", "last_success": None, "consecutive_db_errors": 0}


def _technical(event, **fields):
    log.info(json.dumps({"event": event, **fields}, sort_keys=True))


def run_one():
    now = datetime.now(timezone.utc)
    token = uuid.uuid4().hex
    with SessionLocal() as db:
        eligible = or_(
            and_(Job.status == "PENDING", Job.due_at <= now),
            and_(Job.status == "RUNNING", Job.lease_until <= now),
        )
        candidate = db.scalar(
            select(Job.id).where(eligible).order_by(Job.due_at, Job.id).limit(1)
        )
        if candidate is None:
            return False
        claimed = db.execute(
            update(Job)
            .where(Job.id == candidate, eligible)
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=now + timedelta(minutes=5),
                attempts=Job.attempts + 1,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            return False
        db.commit()
        job = db.get(Job, candidate)
        try:
            payload = json.loads(job.payload)
            if not isinstance(payload, dict):
                raise ValueError("Invalid job payload")
            if job.attempts > MAX_ATTEMPTS:
                raise ValueError("Job exceeded maximum attempts")
            result = evaluate(job.tool_id, payload)
            if result.get("status") == "EXCEPTION":
                raise ValueError("Evaluation failed")
        except (ValueError, TypeError, KeyError):
            status = "QUARANTINED" if job.attempts >= MAX_ATTEMPTS else "PENDING"
            held = db.execute(
                update(Job)
                .where(
                    Job.id == candidate,
                    Job.status == "RUNNING",
                    Job.lease_token == token,
                )
                .values(status=status, lease_token=None, lease_until=None)
            )
            if held.rowcount:
                db.add(
                    Event(
                        event_type="job_failed",
                        reference=f"job:{candidate};status:{status}",
                    )
                )
                db.commit()
                _technical("job_failed", job_id=candidate, status=status)
            else:
                db.rollback()
            return True
        held = db.execute(
            update(Job)
            .where(
                Job.id == candidate, Job.status == "RUNNING", Job.lease_token == token
            )
            .values(lease_until=datetime.now(timezone.utc) + timedelta(minutes=5))
        )
        if held.rowcount != 1:
            db.rollback()
            return True
        run = save_run(db, job.tool_id, result)
        job.status = "DONE"
        job.run_id = run.id
        job.lease_token = None
        job.lease_until = None
        db.add(
            Event(
                event_type="job_finished",
                reference=f"job:{job.id};run:{run.id};status:{result['status']}",
            )
        )
        db.commit()
        return True


def _recoverable(exc):
    # Busy/locked errors are transient; malformed schemas and I/O errors are fatal.
    original = getattr(exc, "orig", exc)
    code = getattr(original, "sqlite_errorcode", None)
    if code is not None:
        return (code & 0xFF) in (5, 6)
    return any(
        word in str(original).lower()
        for word in (
            "database is locked",
            "database is busy",
            "database table is locked",
        )
    )


def _attempt(operation, sleep=time.sleep):
    failures = 0
    while True:
        try:
            value = operation()
            heartbeat.update(
                state="healthy",
                last_success=datetime.now(timezone.utc).isoformat(),
                consecutive_db_errors=0,
            )
            _technical("worker_heartbeat", state="healthy")
            return value
        except (OperationalError, sqlite3.OperationalError) as exc:
            failures += 1
            heartbeat.update(state="database_error", consecutive_db_errors=failures)
            _technical(
                "worker_database_error", recoverable=_recoverable(exc), attempt=failures
            )
            if not _recoverable(exc) or failures >= MAX_DB_FAILURES:
                heartbeat["state"] = "failed"
                raise
            sleep(min(0.25 * 2 ** (failures - 1), 5.0))


def main():
    parser = argparse.ArgumentParser(
        description="Lokaler Worker für reine Testauswertungen"
    )
    parser.add_argument(
        "--once", action="store_true", help="Höchstens einen fälligen Auftrag ausführen"
    )
    parser.add_argument(
        "--interval", type=float, default=5, help="Abfrageintervall in Sekunden"
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval muss größer als 0 sein")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _attempt(init_db)
    if args.once:
        _attempt(run_one)
        return
    while True:
        if not _attempt(run_one):
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
