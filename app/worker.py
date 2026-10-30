"""Durable local-only evaluation worker. Never performs external effects."""
import argparse
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, or_, and_
from .db import SessionLocal, init_db
from .models import Event, Job
from .services import evaluate, save_run

def run_one():
    now = datetime.now(timezone.utc)
    token = uuid.uuid4().hex
    with SessionLocal() as db:
        eligible = or_(and_(Job.status == "PENDING", Job.due_at <= now), and_(Job.status == "RUNNING", Job.lease_until <= now))
        candidate = db.scalar(select(Job.id).where(eligible).order_by(Job.due_at, Job.id).limit(1))
        if candidate is None:
            return False
        claimed = db.execute(update(Job).where(Job.id == candidate, eligible).values(status="RUNNING", lease_token=token, lease_until=now + timedelta(minutes=5), attempts=Job.attempts + 1))
        if claimed.rowcount != 1:
            db.rollback()
            return False
        db.commit()
        job = db.get(Job, candidate)
        result = evaluate(job.tool_id, json.loads(job.payload))
        # A recovered lease may have been claimed by another worker. Persist only while ours remains current.
        held = db.execute(update(Job).where(Job.id == candidate, Job.status == "RUNNING", Job.lease_token == token).values(lease_until=datetime.now(timezone.utc) + timedelta(minutes=5)))
        if held.rowcount != 1:
            db.rollback()
            return True
        run = save_run(db, job.tool_id, result)
        job.status = "DONE"
        job.run_id = run.id
        job.lease_token = None
        job.lease_until = None
        db.add(Event(event_type="job_finished", reference=f"job:{job.id};run:{run.id};status:{result['status']}"))
        db.commit()
        return True

def main():
    parser = argparse.ArgumentParser(description="Lokaler Worker für reine Testauswertungen")
    parser.add_argument("--once", action="store_true", help="Höchstens einen fälligen Auftrag ausführen")
    parser.add_argument("--interval", type=float, default=5, help="Abfrageintervall in Sekunden")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval muss größer als 0 sein")
    init_db()
    if args.once:
        run_one()
        return
    while True:
        if not run_one():
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
