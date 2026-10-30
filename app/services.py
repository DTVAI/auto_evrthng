import hashlib
import importlib
import json
from sqlalchemy import select
from .models import Artifact, Event, TestRun

DOMAINS = ("communication", "recruiting", "personnel", "staffing", "orchestration", "platform")

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()

def catalog():
    from .catalog import catalog as get_catalog
    return get_catalog()

def tool(tool_id):
    return next((item for item in catalog() if item["id"] == tool_id), None)

def domain_for(tool_id):
    for name in DOMAINS:
        try:
            module = importlib.import_module(f".domains.{name}", "app")
        except ModuleNotFoundError as exc:
            if exc.name == f"app.domains.{name}" or exc.name == "app.domains":
                continue
            raise
        if tool_id in module.TOOL_IDS:
            return module
    return None

def tool_info(item):
    module = domain_for(item["id"])
    return {**item, "sample": module.SAMPLES.get(item["id"], {}) if module else None,
            "mode": "local/dry_run", "implementation_status": "implemented" if module else "not_implemented"}

def evaluate(tool_id, payload):
    module = domain_for(tool_id)
    if module is None:
        return {"status": "EXCEPTION", "summary": "Für dieses Werkzeug ist noch keine lokale Auswertung verfügbar.", "data": {}, "checks": [], "artifacts": [], "warnings": ["Keine externe Aktion wurde ausgeführt."]}
    try:
        result = module.run(tool_id, payload)
        if not isinstance(result, dict) or result.get("status") not in {"READY", "NEEDS_DATA", "NEEDS_DECISION", "EXCEPTION"}:
            raise ValueError("Invalid domain result")
        if not isinstance(result.get("summary"), str) or not isinstance(result.get("data"), dict) or not isinstance(result.get("checks"), list) or not isinstance(result.get("artifacts"), list) or not isinstance(result.get("warnings"), list):
            raise ValueError("Invalid domain result")
        encode(result)
        return result
    except Exception:
        return {"status": "EXCEPTION", "summary": "Die lokale Auswertung konnte nicht abgeschlossen werden.", "data": {}, "checks": [], "artifacts": [], "warnings": ["Keine externe Aktion wurde ausgeführt."]}

def save_run(db, tool_id, result, case_id=None):
    run = TestRun(tool_id=tool_id, case_id=case_id, status=result["status"], result=encode(result))
    db.add(run)
    db.flush()
    for artifact in result["artifacts"]:
        if isinstance(artifact, dict) and all(isinstance(artifact.get(k), str) for k in ("name", "content", "media_type")):
            db.add(Artifact(run_id=run.id, case_id=case_id, name=artifact["name"][:255], media_type=artifact["media_type"][:100], content=artifact["content"]))
    db.add(Event(case_id=case_id, event_type="test_run", reference=f"run:{run.id};tool:{tool_id};status:{result['status']}"))
    db.flush()
    return run

def serialize_case(db, case, detail=False):
    from .models import Approval, Evidence, Revision
    value = {"id": case.id, "tool_id": case.tool_id, "title": case.title, "source_ref": case.source_ref, "subject_id": case.subject_id, "revision": case.revision, "payload_hash": case.payload_hash, "status": case.status, "completion_basis": "manual_attestation" if case.status == "COMPLETED" else None, "result": json.loads(case.result), "created_at": case.created_at, "updated_at": case.updated_at}
    if detail:
        value["payload"] = json.loads(case.payload)
        def rows(model):
            return db.scalars(select(model).where(model.case_id == case.id).order_by(model.id)).all()
        value["revisions"] = [{"id": r.id, "revision": r.revision, "payload": json.loads(r.payload), "payload_hash": r.payload_hash, "created_at": r.created_at} for r in rows(Revision)]
        value["approvals"] = [{"id": a.id, "revision": a.revision, "payload_hash": a.payload_hash, "comment": a.comment, "created_at": a.created_at} for a in rows(Approval)]
        value["evidence"] = [{"id": e.id, "revision": e.revision, "kind": e.kind, "reference": e.reference, "observed": json.loads(e.observed), "observed_hash": e.observed_hash, "created_at": e.created_at} for e in rows(Evidence)]
        value["events"] = [{"id": e.id, "event_type": e.event_type, "reference": e.reference, "created_at": e.created_at} for e in rows(Event)]
        value["artifacts"] = [{"id": a.id, "run_id": a.run_id, "name": a.name, "media_type": a.media_type, "download_url": f"/api/artifacts/{a.id}/download"} for a in rows(Artifact)]
    return value
