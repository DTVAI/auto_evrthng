import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app
from app import services, worker
from app.models import Job
from datetime import datetime, timedelta, timezone

@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(worker, "SessionLocal", sessions)
    monkeypatch.setattr(worker, "evaluate", lambda tool_id, payload: {"status": "READY", "summary": "ok", "data": {}, "checks": [], "artifacts": [], "warnings": []})
    app.state.test_sessions = sessions
    monkeypatch.setattr("app.main.init_db", lambda: None)
    monkeypatch.setattr(services, "catalog", lambda: [{"id": "T1"}])
    monkeypatch.setattr(services, "evaluate", lambda tool_id, payload: {"status": "READY", "summary": "ok", "data": {}, "checks": [], "artifacts": [], "warnings": []})
    with TestClient(app, base_url="http://localhost", headers={"X-Toolbox-Request": "1"}) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()

def create(client, payload=None, source="source-1"):
    return client.post("/api/tools/T1/cases", json={"title": "Test", "source_ref": source, "payload": payload or {"value": 1}}).json()

def test_revision_invalidates_approval_and_evidence(client):
    case = create(client)
    ident = case["id"]
    assert client.post(f"/api/cases/{ident}/approve", json={"revision": 1}).status_code == 200
    assert client.post(f"/api/cases/{ident}/evidence", json={"revision": 1, "kind": "independent_readback", "reference": "manual", "observed": {"value": 1}}).status_code == 200
    assert client.patch(f"/api/cases/{ident}", json={"revision": 1, "payload": {"value": 2}}).json()["revision"] == 2
    assert client.post(f"/api/cases/{ident}/approve", json={"revision": 1}).status_code == 409
    assert client.post(f"/api/cases/{ident}/complete", json={"revision": 2}).status_code == 409
    assert client.post(f"/api/cases/{ident}/approve", json={"revision": 2}).status_code == 200
    assert client.post(f"/api/cases/{ident}/evidence", json={"revision": 2, "kind": "independent_readback", "reference": "manual", "observed": {"value": 1}}).status_code == 200
    assert client.post(f"/api/cases/{ident}/complete", json={"revision": 2}).status_code == 409
    assert client.post(f"/api/cases/{ident}/evidence", json={"revision": 2, "kind": "independent_readback", "reference": "manual", "observed": {"value": 2}}).status_code == 200
    assert client.post(f"/api/cases/{ident}/complete", json={"revision": 2}).json()["status"] == "COMPLETED"
    assert client.post(f"/api/cases/{ident}/complete", json={"revision": 2}).status_code == 200

def test_duplicate_source_and_persisted_audit(client):
    first = create(client)
    second = create(client)
    assert client.post("/api/tools/T1/cases", json={"title": "Test", "source_ref": "source-1", "payload": {"value": 100}}).status_code == 409
    assert first["id"] == second["id"]
    detail = client.get(f"/api/cases/{first['id']}").json()
    assert detail["payload"] == {"value": 1}
    assert len(detail["revisions"]) == 1
    assert len(client.get("/api/cases").json()) == 1
    assert client.get("/api/dashboard").json()["test_runs"] == 1

def test_invalid_and_local_security(client):
    assert client.post("/api/tools/T1/cases", json={"title": "", "payload": {}}).status_code == 422
    assert client.post("/api/tools/missing/test", json={}).status_code == 404
    assert client.post("/api/tools/T1/test", json={}, headers={"X-Toolbox-Request": ""}).status_code == 403
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/api/health", headers={"Origin": "http://evil.example"}).status_code == 403


def test_durable_jobs_due_and_recover_expired_lease(client):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    queued = client.post("/api/jobs", json={"tool_id": "T1", "payload": {"x": 1}, "due_at": future}).json()
    assert worker.run_one() is False
    with app.state.test_sessions() as db:
        job = db.get(Job, queued["id"])
        job.status = "RUNNING"
        job.lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        job.lease_token = "crashed"
        db.commit()
    assert worker.run_one() is True
    row = client.get("/api/jobs").json()[0]
    assert row["status"] == "DONE" and row["attempts"] == 1 and row["run_id"]
    assert client.get(f"/api/runs/{row['run_id']}").json()["status"] == "READY"
    assert worker.run_one() is False
    assert client.post("/api/jobs", json={"tool_id": "T1", "payload": {}, "due_at": "2030-01-01T12:00:00"}).status_code == 422


def test_job_idempotency_and_conflict(client):
    body = {"tool_id": "T1", "payload": {"value": 1}, "idempotency_key": "same-key"}
    first = client.post("/api/jobs", json=body)
    again = client.post("/api/jobs", json=body)
    assert first.status_code == again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    changed = {**body, "payload": {"value": 2}}
    assert client.post("/api/jobs", json=changed).status_code == 409
    assert len(client.get("/api/jobs").json()) == 1
    assert client.post("/api/jobs", json={**body, "idempotency_key": " "}).status_code == 422
