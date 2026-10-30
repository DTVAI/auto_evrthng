from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db, init_db
from .models import (
    Approval,
    Artifact,
    Case,
    Evidence,
    Event,
    Revision,
    TestRun,
    Job,
    JobRequest,
)
from . import services
from .imports import router as imports_router, strict_json
from .workflows import router as workflows_router
from .workflow_models import CaseClaim
import json


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="HR Werkzeugkasten", lifespan=lifespan)
app.include_router(imports_router)
app.include_router(workflows_router)


@app.middleware("http")
async def local_security(request: Request, call_next):
    host = request.headers.get("host", "")
    try:
        parsed_host = urlsplit("http://" + host)
        valid_host = (
            parsed_host.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed_host.username is None
            and parsed_host.path == ""
            and parsed_host.port != 0
        )
        origin = request.headers.get("origin")
        if origin:
            parsed_origin = urlsplit(origin)
            valid_origin = (
                parsed_origin.scheme in {"http", "https"}
                and parsed_origin.netloc == host
                and parsed_origin.path == ""
                and not parsed_origin.query
                and not parsed_origin.fragment
            )
        else:
            valid_origin = True
    except ValueError:
        valid_host = valid_origin = False
    if not valid_host or not valid_origin:
        return JSONResponse(
            {"detail": "Nur lokale Anfragen derselben Herkunft sind erlaubt."},
            status_code=403,
        )
    if (
        request.url.path.startswith("/api/")
        and request.method not in {"GET", "HEAD", "OPTIONS"}
        and request.headers.get("X-Toolbox-Request") != "1"
    ):
        return JSONResponse(
            {"detail": "X-Toolbox-Request: 1 ist erforderlich."}, status_code=403
        )
    if request.url.path.startswith("/api/") and request.method in {
        "POST",
        "PATCH",
        "PUT",
    }:
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 1_000_000:
                return JSONResponse(
                    {"detail": "Die Anfrage ist zu groß."}, status_code=413
                )
            chunks.append(chunk)
        body = b"".join(chunks)
        try:
            data = strict_json(body)
            check_structure(data)
            request._body = body
        except (ValueError, UnicodeError, RecursionError):
            return JSONResponse(
                {
                    "detail": "Ungültiges JSON: doppelte Schlüssel und nicht endliche Zahlen sind nicht erlaubt."
                },
                status_code=422,
            )
    return await call_next(request)


def check_structure(value):
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 32 or count > 50000:
            raise ValueError("JSON-Struktur zu groß")
        if isinstance(item, dict):
            if len(item) > 10000:
                raise ValueError("Objekt zu groß")
            stack.extend((key, depth + 1) for key in item)
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            if len(item) > 10000:
                raise ValueError("Liste zu groß")
            stack.extend((v, depth + 1) for v in item)
        elif isinstance(item, str) and len(item) > 800000:
            raise ValueError("Zeichenkette zu groß")


def validate_payload(tool_id, payload):
    try:
        services.validate(tool_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    payload: dict
    source_ref: str | None = Field(default=None, max_length=300)
    subject_id: str | None = Field(default=None, max_length=200)


class CasePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    payload: dict
    title: str | None = Field(default=None, min_length=1, max_length=300)


class Approve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    comment: str = Field(default="", max_length=4000)


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    kind: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=500)
    observed: dict


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_id: str = Field(min_length=1, max_length=80)
    payload: dict
    due_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class Complete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)


def get_case(db, case_id):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Vorgang nicht gefunden.")
    return case


def current(case, revision):
    if case.revision != revision:
        raise HTTPException(
            409, "Die Revision ist veraltet. Bitte den Vorgang neu laden."
        )


def lock_revision(db, case_id, revision):
    locked = db.execute(
        update(Case)
        .where(Case.id == case_id, Case.revision == revision)
        .values(revision=Case.revision)
    )
    if locked.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Die Revision ist veraltet.")


def source_matches(db, case, payload, subject_id):
    first = db.scalar(
        select(Revision).where(Revision.case_id == case.id, Revision.revision == 1)
    )
    return (
        first is not None
        and first.payload_hash == services.digest(payload)
        and first.subject_id == subject_id
    )


def known(tool_id):
    item = services.tool(tool_id)
    if not item:
        raise HTTPException(404, "Werkzeug nicht gefunden.")
    return item


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local/dry_run"}


@app.get("/api/integrations")
def integrations():
    return {
        "mode": "local/dry_run",
        "adapters": [
            {
                "id": "manual",
                "status": "manual",
                "description": "Externe Schritte werden außerhalb der Anwendung ausgeführt und manuell belegt.",
            }
        ],
        "external_actions_enabled": False,
    }


@app.get("/api/tools")
def tools():
    return [services.tool_info(x) for x in services.catalog()]


@app.get("/api/tools/{tool_id}")
def get_tool(tool_id: str):
    return services.tool_info(known(tool_id))


@app.post("/api/tools/{tool_id}/test")
def test_tool(tool_id: str, payload: dict, db: Session = Depends(get_db)):
    known(tool_id)
    validate_payload(tool_id, payload)
    result = services.evaluate(tool_id, payload)
    run = services.save_run(db, tool_id, result)
    artifacts = [
        {
            "id": a.id,
            "name": a.name,
            "media_type": a.media_type,
            "download_url": f"/api/artifacts/{a.id}/download",
        }
        for a in db.scalars(select(Artifact).where(Artifact.run_id == run.id)).all()
    ]
    db.commit()
    return {**result, "run_id": run.id, "persisted_artifacts": artifacts}


@app.post("/api/tools/{tool_id}/cases")
def create_case(tool_id: str, body: CaseCreate, db: Session = Depends(get_db)):
    known(tool_id)
    source = (body.source_ref.strip() or None) if body.source_ref else None
    if source:
        existing = db.scalar(
            select(Case).where(Case.tool_id == tool_id, Case.source_ref == source)
        )
        if existing:
            if not source_matches(db, existing, body.payload, body.subject_id):
                raise HTTPException(
                    409, "Die Quellreferenz ist bereits mit anderen Daten belegt."
                )
            return services.serialize_case(db, existing, True)
    validate_payload(tool_id, body.payload)
    result = services.evaluate(tool_id, body.payload)
    case = Case(
        tool_id=tool_id,
        title=body.title,
        subject_id=body.subject_id,
        source_ref=source,
        payload=services.encode(body.payload),
        payload_hash=services.digest(body.payload),
        revision=1,
        status="OPEN",
        result=services.encode(result),
    )
    db.add(case)
    try:
        db.flush()
        db.add(
            Revision(
                case_id=case.id,
                revision=1,
                payload=case.payload,
                payload_hash=case.payload_hash,
                title=case.title,
                subject_id=case.subject_id,
            )
        )
        db.add(
            Event(
                case_id=case.id,
                event_type="created",
                reference=f"tool:{tool_id};revision:1",
            )
        )
        services.save_run(db, tool_id, result, case.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.scalar(
                select(Case).where(Case.tool_id == tool_id, Case.source_ref == source)
            )
            if source
            else None
        )
        if existing:
            if not source_matches(db, existing, body.payload, body.subject_id):
                raise HTTPException(
                    409, "Die Quellreferenz ist bereits mit anderen Daten belegt."
                )
            return services.serialize_case(db, existing, True)
        raise
    return services.serialize_case(db, case, True)


@app.get("/api/cases")
def list_cases(identity: str | None = None, db: Session = Depends(get_db)):
    query = select(Case).order_by(Case.id.desc())
    if identity is not None:
        identity = identity.strip()
        if not identity:
            raise HTTPException(422, "Identität erforderlich.")
        query = query.join(CaseClaim, CaseClaim.case_id == Case.id).where(
            (CaseClaim.identity == identity) | (CaseClaim.deputy_for == identity)
        )
    return [services.serialize_case(db, c) for c in db.scalars(query).all()]


@app.get("/api/cases/{case_id}")
def case_detail(case_id: int, db: Session = Depends(get_db)):
    return services.serialize_case(db, get_case(db, case_id), True)


@app.patch("/api/cases/{case_id}")
def patch_case(case_id: int, body: CasePatch, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    current(case, body.revision)
    validate_payload(case.tool_id, body.payload)
    result = services.evaluate(case.tool_id, body.payload)
    data = services.encode(body.payload)
    hashed = services.digest(body.payload)
    values = {
        "payload": data,
        "payload_hash": hashed,
        "revision": body.revision + 1,
        "status": "OPEN",
        "result": services.encode(result),
    }
    if body.title is not None:
        values["title"] = body.title
    changed = db.execute(
        update(Case)
        .where(Case.id == case_id, Case.revision == body.revision)
        .values(**values)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Die Revision ist veraltet.")
    db.add(
        Revision(
            case_id=case_id,
            revision=body.revision + 1,
            payload=data,
            payload_hash=hashed,
            title=body.title if body.title is not None else case.title,
            subject_id=case.subject_id,
        )
    )
    db.add(
        Event(
            case_id=case_id,
            event_type="revised",
            reference=f"revision:{body.revision + 1}",
        )
    )
    services.save_run(db, case.tool_id, result, case_id)
    from .workflows import invalidate_case

    invalidate_case(db, case_id)
    db.commit()
    db.refresh(case)
    return services.serialize_case(db, case, True)


@app.post("/api/cases/{case_id}/approve")
def approve(case_id: int, body: Approve, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    current(case, body.revision)
    lock_revision(db, case_id, body.revision)
    existing = db.scalar(
        select(Approval).where(
            Approval.case_id == case.id,
            Approval.revision == case.revision,
            Approval.payload_hash == case.payload_hash,
        )
    )
    if not existing:
        db.add(
            Approval(
                case_id=case.id,
                revision=case.revision,
                payload_hash=case.payload_hash,
                comment=body.comment,
            )
        )
        db.add(
            Event(
                case_id=case.id,
                event_type="approved",
                reference=f"revision:{case.revision};hash:{case.payload_hash}",
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return services.serialize_case(db, case, True)


@app.post("/api/cases/{case_id}/evidence")
def evidence(case_id: int, body: EvidenceCreate, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    current(case, body.revision)
    lock_revision(db, case_id, body.revision)
    if not body.kind.strip() or not body.reference.strip():
        raise HTTPException(422, "Art und Referenz sind erforderlich.")
    observed = services.encode(body.observed)
    existing = db.scalar(
        select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.revision == body.revision,
            Evidence.kind == body.kind,
            Evidence.reference == body.reference,
            Evidence.observed == observed,
        )
    )
    if not existing:
        db.add(
            Evidence(
                case_id=case.id,
                revision=body.revision,
                kind=body.kind,
                reference=body.reference,
                observed=observed,
                observed_hash=services.digest(body.observed),
            )
        )
        db.add(
            Event(
                case_id=case.id,
                event_type="evidence_recorded",
                reference=f"revision:{case.revision}",
            )
        )
        db.commit()
    return services.serialize_case(db, case, True)


@app.post("/api/cases/{case_id}/complete")
def complete(case_id: int, body: Complete, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    current(case, body.revision)
    if case.status == "COMPLETED":
        return services.serialize_case(db, case, True)
    approval = db.scalar(
        select(Approval).where(
            Approval.case_id == case.id,
            Approval.revision == case.revision,
            Approval.payload_hash == case.payload_hash,
        )
    )
    from .projections import expected, matches

    target = expected(case.tool_id, json.loads(case.payload), case.subject_id)
    candidates = db.scalars(
        select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.revision == case.revision,
            Evidence.kind == "independent_readback",
            Evidence.reference != "",
        )
    ).all()
    proof = next(
        (e for e in candidates if matches(target, json.loads(e.observed))), None
    )
    if not approval or not proof:
        raise HTTPException(
            409,
            "Abschluss benötigt eine Freigabe und eine manuell dokumentierte unabhängige Rücklesung mit Quellenreferenz für die aktuelle Revision.",
        )
    if json.loads(case.result)["status"] != "READY":
        raise HTTPException(409, "Die aktuelle lokale Prüfung ist noch nicht bereit.")
    changed = db.execute(
        update(Case)
        .where(
            Case.id == case_id, Case.revision == body.revision, Case.status == "OPEN"
        )
        .values(status="COMPLETED")
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Der Vorgang wurde zwischenzeitlich geändert.")
    db.add(
        Event(
            case_id=case.id,
            event_type="completed",
            reference=f"revision:{case.revision};approval:{approval.id};evidence:{proof.id}",
        )
    )
    db.commit()
    db.refresh(case)
    return services.serialize_case(db, case, True)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if not run:
        raise HTTPException(404, "Prüfung nicht gefunden.")
    artifacts = [
        {
            "id": a.id,
            "name": a.name,
            "media_type": a.media_type,
            "download_url": f"/api/artifacts/{a.id}/download",
        }
        for a in db.scalars(select(Artifact).where(Artifact.run_id == run.id)).all()
    ]
    return {
        **json.loads(run.result),
        "run_id": run.id,
        "tool_id": run.tool_id,
        "case_id": run.case_id,
        "created_at": services.utc(run.created_at),
        "persisted_artifacts": artifacts,
    }


@app.get("/api/artifacts/{artifact_id}/download")
def download(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(404, "Artefakt nicht gefunden.")
    from urllib.parse import quote

    return Response(
        artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(artifact.name, safe=""),
            "X-Content-Type-Options": "nosniff",
        },
    )


def serialize_job(job):
    return {
        "id": job.id,
        "tool_id": job.tool_id,
        "status": job.status,
        "due_at": services.utc(job.due_at),
        "lease_until": services.utc(job.lease_until),
        "attempts": job.attempts,
        "run_id": job.run_id,
        "created_at": services.utc(job.created_at),
    }


@app.get("/api/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return [
        serialize_job(j) for j in db.scalars(select(Job).order_by(Job.id.desc())).all()
    ]


@app.post("/api/jobs")
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    known(body.tool_id)
    validate_payload(body.tool_id, body.payload)
    if body.due_at and body.due_at.tzinfo is None:
        raise HTTPException(422, "Fälligkeitszeit muss eine Zeitzone enthalten.")
    key = body.idempotency_key
    if key is not None and not key.strip():
        raise HTTPException(422, "Der Wiederholungsschlüssel darf nicht leer sein.")
    due = body.due_at.astimezone(timezone.utc) if body.due_at else None
    request_hash = services.digest(
        {
            "tool_id": body.tool_id,
            "payload": body.payload,
            "due_at": due.isoformat() if due else None,
        }
    )

    def replay():
        record = db.scalar(select(JobRequest).where(JobRequest.idempotency_key == key))
        if not record:
            return None
        if record.request_hash != request_hash:
            raise HTTPException(
                409,
                "Der Wiederholungsschlüssel ist bereits mit einem anderen Auftrag belegt.",
            )
        return db.get(Job, record.job_id)

    if key is not None:
        existing = replay()
        if existing:
            return serialize_job(existing)
    job = Job(
        tool_id=body.tool_id,
        payload=services.encode(body.payload),
        status="PENDING",
        due_at=due or datetime.now(timezone.utc),
    )
    db.add(job)
    try:
        db.flush()
        if key is not None:
            db.add(
                JobRequest(
                    idempotency_key=key, request_hash=request_hash, job_id=job.id
                )
            )
        db.add(
            Event(
                event_type="job_queued", reference=f"job:{job.id};tool:{body.tool_id}"
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        if key is not None:
            existing = replay()
            if existing:
                return serialize_job(existing)
        raise
    return serialize_job(job)


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    outcomes = dict(
        db.execute(
            select(TestRun.status, func.count(TestRun.id)).group_by(TestRun.status)
        ).all()
    )
    cases = dict(
        db.execute(select(Case.status, func.count(Case.id)).group_by(Case.status)).all()
    )
    return {
        "tool_count": len(services.catalog()),
        "test_runs": sum(outcomes.values()),
        "outcomes": outcomes,
        "case_count": sum(cases.values()),
        "cases": cases,
        "mode": "local/dry_run",
    }


static = Path(__file__).parent / "static"
static.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static), name="static")


@app.get("/", include_in_schema=False)
def index():
    path = static / "index.html"
    if not path.is_file():
        raise HTTPException(404, "Oberfläche noch nicht verfügbar.")
    return FileResponse(path)
