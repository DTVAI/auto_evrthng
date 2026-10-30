import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import worker
from app.db import Base
from app.models import Job, TestRun as RunRecord


def test_private_database_foreign_keys_and_legacy_migration(tmp_path):
    path = tmp_path / "app.db"
    env = dict(os.environ, TOOLBOX_DATABASE_URL=f"sqlite:///{path}")
    script = 'import os; os.umask(0o022); from app.db import init_db, engine; init_db(); assert engine.connect().exec_driver_sql("PRAGMA foreign_keys").scalar() == 1'
    subprocess.run([sys.executable, "-c", script], env=env, check=True)
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute(
            "INSERT INTO cases VALUES (1,'O01','Current','person',NULL,'{}','hash',1,'OPEN','{}','2026-01-01','2026-01-01')"
        )
        db.execute("DROP TABLE revisions")
        db.execute(
            "CREATE TABLE revisions (id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL REFERENCES cases(id), revision INTEGER NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, created_at DATETIME NOT NULL)"
        )
        db.execute("INSERT INTO revisions VALUES (1,1,1,'{}','hash','2026-01-01')")
        db.execute("PRAGMA user_version=0")
        db.execute("PRAGMA application_id=0")
    subprocess.run([sys.executable, "-c", script], env=env, check=True)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT title,subject_id FROM revisions").fetchone() == (
            None,
            None,
        )
        assert db.execute("PRAGMA user_version").fetchone() == (2,)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO revisions (case_id,revision,payload,payload_hash,created_at) VALUES (1,1,'{}','hash','2026-01-01')"
            )


def test_worker_recovers_lock_and_quarantines_bad_job(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'worker.db'}", connect_args={"timeout": 0}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", sessions)
    with sessions.begin() as db:
        db.add_all(
            [
                Job(
                    tool_id="O01",
                    payload="bad",
                    status="PENDING",
                    due_at=datetime.now(timezone.utc),
                ),
                Job(
                    tool_id="O01",
                    payload="{}",
                    status="PENDING",
                    due_at=datetime.now(timezone.utc),
                ),
            ]
        )
    monkeypatch.setattr(
        worker,
        "evaluate",
        lambda *_: {
            "status": "READY",
            "summary": "ok",
            "data": {},
            "checks": [],
            "artifacts": [],
            "warnings": [],
        },
    )
    lock = sqlite3.connect(tmp_path / "worker.db")
    lock.execute("BEGIN EXCLUSIVE")
    sleeps = []

    def unlock(delay):
        sleeps.append(delay)
        lock.rollback()

    assert worker._attempt(worker.run_one, sleep=unlock)
    assert sleeps and worker.heartbeat["state"] == "healthy"
    assert worker.run_one()
    assert worker.run_one()
    assert worker.run_one()
    with sessions() as db:
        jobs = db.scalars(select(Job).order_by(Job.id)).all()
        assert jobs[0].status == "QUARANTINED" and jobs[0].attempts == 3
        assert jobs[1].status == "DONE"
    lock.close()


def test_worker_lost_lease_cannot_save_result(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'lease.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", sessions)
    with sessions.begin() as db:
        db.add(
            Job(
                tool_id="O01",
                payload="{}",
                status="PENDING",
                due_at=datetime.now(timezone.utc),
            )
        )

    def take_lease(*_):
        with sessions.begin() as db:
            job = db.get(Job, 1)
            job.lease_token = "other-worker"
        return {
            "status": "READY",
            "summary": "ok",
            "data": {},
            "checks": [],
            "artifacts": [],
            "warnings": [],
        }

    monkeypatch.setattr(worker, "evaluate", take_lease)
    assert worker.run_one()
    with sessions() as db:
        assert db.get(Job, 1).lease_token == "other-worker"
        assert db.scalars(select(RunRecord)).all() == []


def test_schema_validation_rejects_missing_foreign_keys(tmp_path):
    from sqlalchemy import UniqueConstraint
    from sqlalchemy.dialects.sqlite import dialect
    from app import workflow_models  # noqa: F401
    from app.migrations import validate_schema

    path = tmp_path / "missing-foreign-keys.db"
    with sqlite3.connect(path) as db:
        for table in Base.metadata.sorted_tables:
            definitions = []
            for column in table.columns:
                declaration = (
                    f'"{column.name}" {column.type.compile(dialect=dialect())}'
                )
                if not column.nullable and not column.primary_key:
                    declaration += " NOT NULL"
                definitions.append(declaration)
            pk = ", ".join(f'"{col.name}"' for col in table.primary_key.columns)
            definitions.append(f"PRIMARY KEY ({pk})")
            for constraint in table.constraints:
                if isinstance(constraint, UniqueConstraint):
                    cols = ", ".join(f'"{col.name}"' for col in constraint.columns)
                    definitions.append(f"UNIQUE ({cols})")
            db.execute(f'CREATE TABLE "{table.name}" ({", ".join(definitions)})')
            for index in table.indexes:
                if index.unique:
                    cols = ", ".join(f'"{col.name}"' for col in index.columns)
                    db.execute(
                        f'CREATE UNIQUE INDEX "{index.name}" ON "{table.name}" ({cols})'
                    )
        with pytest.raises(ValueError, match="foreign key missing"):
            validate_schema(db, 2)
