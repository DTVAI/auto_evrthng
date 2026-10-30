"""Local, persisted workflows. Inputs are keyed by step; all effects remain manual."""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db
from .models import Case, now
from .workflow_models import Workflow, WorkflowStep, WorkflowEvent, CaseClaim
from . import services

router = APIRouter()
# The graph is persisted per step, so previous generations remain inspectable.
SPECS = {
    "hours_change": [
        ("change", "P02", []),
        ("draft", "P05", ["change"]),
        ("hr_record", "P04", ["change", "draft"]),
    ],
    "start_shift": [
        ("event", "O01", []),
        ("tasks", "O02", ["event"]),
        ("document", "P05", ["event"]),
        ("commitments", "O13", ["tasks", "document"]),
    ],
    "staffing_invoice": [
        ("hours", "A05", []),
        ("invoice", "A06", ["hours"]),
        ("correction", "A07", ["invoice"]),
    ],
}


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    title: str = Field(min_length=1, max_length=300)
    payload: dict
    source_ref: str | None = Field(default=None, max_length=300)


class Patch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    payload: dict
    title: str | None = Field(default=None, min_length=1, max_length=300)


class Attach(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    case_id: int


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity: str = Field(min_length=1, max_length=200)
    deputy_for: str | None = Field(default=None, max_length=200)


def check_input(kind, payload):
    if kind not in SPECS:
        raise HTTPException(422, "Unbekannte Fallkette.")
    if set(payload) - {x[0] for x in SPECS[kind]}:
        raise HTTPException(422, "Unbekannter Schritt in payload.")
    if any(not isinstance(v, dict) for v in payload.values()):
        raise HTTPException(422, "Schritteingaben müssen Objekte sein.")
    for key, tool, _ in SPECS[kind]:
        if key in payload:
            try:
                services.validate(tool, payload[key])
            except ValueError as exc:
                raise HTTPException(422, f"{key}: {exc}") from exc


def get_workflow(db, ident):
    w = db.get(Workflow, ident)
    if not w:
        raise HTTPException(404, "Fallkette nicht gefunden.")
    return w


def steps(db, w):
    return db.scalars(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == w.id)
        .order_by(WorkflowStep.id)
    ).all()


def make_step(db, w, key, tool, deps, payload, generation):
    data = payload.get(key)
    result = (
        services.evaluate(tool, data)
        if data is not None
        else {
            "status": "NEEDS_DATA",
            "summary": "Schritteingabe fehlt.",
            "data": {},
            "checks": [],
            "artifacts": [],
            "warnings": [],
        }
    )
    db.add(
        WorkflowStep(
            workflow_id=w.id,
            key=key,
            generation=generation,
            tool_id=tool,
            dependencies=services.encode(deps),
            input=services.encode(data),
            result=services.encode(result),
            status=result["status"],
        )
    )


def serialize(db, w):
    rows = steps(db, w)
    active = {s.key: s for s in rows if s.active}

    def step(s):
        deps = json.loads(s.dependencies)
        case = db.get(Case, s.case_id) if s.case_id else None
        valid = bool(
            case and case.revision == s.case_revision and case.status == "COMPLETED"
        )
        status = s.status
        if s.active and status == "COMPLETED" and not valid:
            status = "STALE"
        if (
            s.active
            and status != "COMPLETED"
            and any(
                not (
                    w.kind == "staffing_invoice"
                    and s.key == "correction"
                    and d == "invoice"
                    and active[d].status == "NEEDS_DECISION"
                )
                and (
                    active[d].status != "COMPLETED"
                    or not active[d].case_id
                    or (
                        db.get(Case, active[d].case_id).revision
                        != active[d].case_revision
                    )
                )
                for d in deps
            )
        ):
            status = "BLOCKED"
        return {
            "id": s.id,
            "key": s.key,
            "generation": s.generation,
            "tool_id": s.tool_id,
            "depends_on": deps,
            "status": status,
            "result": json.loads(s.result),
            "case_id": s.case_id,
            "case_revision": s.case_revision,
            "active": bool(s.active),
            "created_at": services.utc(s.created_at),
            "completed_at": services.utc(s.completed_at),
        }

    events = db.scalars(
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_id == w.id)
        .order_by(WorkflowEvent.id)
    ).all()
    current = [step(s) for s in rows if s.active]
    complete = bool(current) and all(s["status"] == "COMPLETED" for s in current)
    # Elapsed time is measurable; active/wait intervals are not tracked.
    from datetime import datetime

    start = datetime.fromisoformat(services.utc(w.created_at))
    end = (
        max(
            (
                datetime.fromisoformat(s["completed_at"])
                for s in current
                if s["completed_at"]
            ),
            default=start,
        )
        if complete
        else now()
    )
    elapsed = max(0.0, (end - start).total_seconds())
    return {
        "id": w.id,
        "kind": w.kind,
        "title": w.title,
        "source_ref": w.source_ref,
        "revision": w.revision,
        "payload": json.loads(w.payload),
        "created_at": services.utc(w.created_at),
        "updated_at": services.utc(w.updated_at),
        "status": "COMPLETED"
        if current and all(s["status"] == "COMPLETED" for s in current)
        else "OPEN",
        "steps": current,
        "history": [step(s) for s in rows if not s.active],
        "events": [
            {
                "id": e.id,
                "type": e.event_type,
                "revision": e.revision,
                "step": e.step_key,
                "created_at": services.utc(e.created_at),
            }
            for e in events
        ],
        "metrics": {
            "steps_total": len(current),
            "steps_completed": sum(s["status"] == "COMPLETED" for s in current),
            "corrections": sum(e.event_type == "revised" for e in events),
            "missing_inputs": sum(
                s["result"]["status"] == "NEEDS_DATA" for s in current
            ),
            "event_count": len(events),
            "elapsed_seconds": elapsed,
            "elapsed_basis": "created_to_completion" if complete else "created_to_now",
            "active_seconds": None,
            "waiting_seconds": None,
        },
    }


@router.post("/api/workflows")
def create(body: Create, db: Session = Depends(get_db)):
    check_input(body.kind, body.payload)
    source = (body.source_ref.strip() or None) if body.source_ref else None

    def replay():
        old = (
            db.scalar(
                select(Workflow).where(
                    Workflow.kind == body.kind, Workflow.source_ref == source
                )
            )
            if source
            else None
        )
        if old:
            original = {
                s.key: json.loads(s.input)
                for s in steps(db, old)
                if s.generation == 1 and json.loads(s.input) is not None
            }
            if original != body.payload:
                raise HTTPException(409, "Quellreferenz bereits anders belegt.")
        return old

    old = replay()
    if old:
        return serialize(db, old)
    w = Workflow(
        kind=body.kind,
        title=body.title,
        source_ref=source,
        payload=services.encode(body.payload),
        revision=1,
    )
    db.add(w)
    try:
        db.flush()
        for key, tool, deps in SPECS[w.kind]:
            make_step(db, w, key, tool, deps, body.payload, 1)
        db.add(WorkflowEvent(workflow_id=w.id, revision=1, event_type="created"))
        db.commit()
    except IntegrityError:
        db.rollback()
        old = replay()
        if old:
            return serialize(db, old)
        raise
    return serialize(db, w)


@router.get("/api/workflows")
def listing(db: Session = Depends(get_db)):
    return [
        serialize(db, w)
        for w in db.scalars(select(Workflow).order_by(Workflow.id.desc())).all()
    ]


@router.get("/api/workflows/{ident}")
def detail(ident: int, db: Session = Depends(get_db)):
    return serialize(db, get_workflow(db, ident))


@router.patch("/api/workflows/{ident}")
def revise(ident: int, body: Patch, db: Session = Depends(get_db)):
    w = get_workflow(db, ident)
    check_input(w.kind, body.payload)
    old = json.loads(w.payload)
    changed = {k for k, _, _ in SPECS[w.kind] if old.get(k) != body.payload.get(k)}
    affected = set(changed)
    for key, _, deps in SPECS[w.kind]:
        if affected.intersection(deps):
            affected.add(key)
    values = {"payload": services.encode(body.payload), "revision": body.revision + 1}
    if body.title is not None:
        values["title"] = body.title
    if (
        db.execute(
            update(Workflow)
            .where(Workflow.id == ident, Workflow.revision == body.revision)
            .values(**values)
        ).rowcount
        != 1
    ):
        db.rollback()
        raise HTTPException(409, "Revision veraltet.")
    for row in steps(db, w):
        if row.active and row.key in affected:
            row.active = 0
    for key, tool, deps in SPECS[w.kind]:
        if key in affected:
            make_step(db, w, key, tool, deps, body.payload, body.revision + 1)
    db.add(
        WorkflowEvent(
            workflow_id=w.id, revision=body.revision + 1, event_type="revised"
        )
    )
    db.commit()
    db.refresh(w)
    return serialize(db, w)


def check_consistency(w, key, payload):
    """Require related steps to refer to the same concrete target."""

    def same(a, b):
        return a is not None and type(a) is type(b) and a == b

    if w.kind == "hours_change":
        change = payload.get("change", {})
        if key == "hr_record":
            target = payload.get("hr_record", {})
            if not all(
                same(change.get(k), target.get(k))
                for k in ("person_id", "new", "valid_from")
            ):
                raise HTTPException(
                    409,
                    "HR-Ziel muss Person, neuen Wert und Gültigkeitsdatum der Stundenänderung enthalten.",
                )
        if key == "draft":
            from string import Formatter

            draft = payload.get("draft", {})
            fields = draft.get("fields", {})
            placeholders = {
                name
                for _, name, _, _ in Formatter().parse(draft.get("template", ""))
                if name
            }
            if not all(
                k in placeholders and same(change.get(k), fields.get(k))
                for k in ("person_id", "new", "valid_from")
            ):
                raise HTTPException(
                    409,
                    "Entwurf benötigt passende Platzhalter person_id, new und valid_from.",
                )
    if w.kind == "start_shift":
        event = payload.get("event", {}).get("event", {})
        if key == "tasks" and not same(
            event.get("date"), payload.get("tasks", {}).get("target_date")
        ):
            raise HTTPException(409, "Aufgabenplan muss den Ereignistermin verwenden.")
        if key == "document":
            from string import Formatter

            draft = payload.get("document", {})
            fields = draft.get("fields", {})
            placeholders = {
                name
                for _, name, _, _ in Formatter().parse(draft.get("template", ""))
                if name
            }
            if not all(
                k in placeholders and same(event.get(k), fields.get(k))
                for k in ("person_id", "date")
            ):
                raise HTTPException(
                    409, "Dokument benötigt passende Platzhalter person_id und date."
                )
    if w.kind == "staffing_invoice":
        invoice = payload.get("invoice", {})
        if key == "invoice":
            hours = payload.get("hours", {})
            actual = {
                str(x.get("id")): str(x.get("hours"))
                for x in hours.get("time_lines", [])
            }
            confirmed = {
                str(x.get("id")): str(x.get("hours"))
                for x in invoice.get("confirmed_lines", [])
            }
            if not actual or actual != confirmed:
                raise HTTPException(
                    409,
                    "Bestätigte Rechnungsstunden müssen den abgestimmten Zeitpositionen entsprechen.",
                )
        if key == "correction" and not same(
            invoice.get("invoice_number"),
            payload.get("correction", {}).get("invoice_number"),
        ):
            raise HTTPException(409, "Korrektur muss dieselbe Rechnung betreffen.")


@router.post("/api/workflows/{ident}/steps/{step_id}/attach")
def attach(ident: int, step_id: int, body: Attach, db: Session = Depends(get_db)):
    w = get_workflow(db, ident)
    if (
        db.execute(
            update(Workflow)
            .where(Workflow.id == ident, Workflow.revision == body.revision)
            .values(revision=Workflow.revision)
        ).rowcount
        != 1
    ):
        db.rollback()
        raise HTTPException(409, "Revision veraltet.")
    row = db.get(WorkflowStep, step_id)
    case = db.get(Case, body.case_id)
    if not row or row.workflow_id != ident or not row.active:
        raise HTTPException(404, "Aktiver Schritt nicht gefunden.")
    if (
        not case
        or case.tool_id != row.tool_id
        or json.loads(case.payload) != json.loads(row.input)
        or case.status != "COMPLETED"
    ):
        raise HTTPException(
            409, "Abgeschlossener Fall mit passender Eingabe und Werkzeug erforderlich."
        )
    check_consistency(w, row.key, json.loads(w.payload))
    state = serialize(db, w)
    if next(x for x in state["steps"] if x["id"] == step_id)["status"] == "BLOCKED":
        raise HTTPException(409, "Abhängiger Schritt ist noch offen.")
    if (
        row.status != "COMPLETED"
        or row.case_id != case.id
        or row.case_revision != case.revision
    ):
        row.case_id = case.id
        row.case_revision = case.revision
        row.status = "COMPLETED"
        row.completed_at = now()
        db.add(
            WorkflowEvent(
                workflow_id=w.id,
                revision=w.revision,
                event_type="step_completed",
                step_key=row.key,
            )
        )
        db.commit()
    return serialize(db, w)


@router.post("/api/cases/{case_id}/claim")
def claim(case_id: int, body: Claim, db: Session = Depends(get_db)):
    identity = body.identity.strip()
    deputy = body.deputy_for.strip() if body.deputy_for else None
    if not identity or (body.deputy_for is not None and not deputy):
        raise HTTPException(422, "Identität erforderlich.")
    if not db.get(Case, case_id):
        raise HTTPException(404, "Vorgang nicht gefunden.")
    claim = db.get(CaseClaim, case_id)
    if claim:
        if claim.identity != identity or claim.deputy_for != deputy:
            raise HTTPException(409, "Vorgang ist bereits übernommen.")
    else:
        db.add(CaseClaim(case_id=case_id, identity=identity, deputy_for=deputy))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Vorgang ist bereits übernommen.")
    return {
        "case_id": case_id,
        "identity": identity,
        "deputy_for": deputy,
        "scope": "local_identity",
    }


@router.post("/api/cases/{case_id}/release")
def release(case_id: int, body: Claim, db: Session = Depends(get_db)):
    claim = db.get(CaseClaim, case_id)
    if not claim:
        raise HTTPException(404, "Keine Übernahme vorhanden.")
    if claim.identity != body.identity.strip() or claim.deputy_for != (
        body.deputy_for.strip() if body.deputy_for else None
    ):
        raise HTTPException(409, "Identität stimmt nicht überein.")
    db.delete(claim)
    db.commit()
    return {"case_id": case_id, "released": True}


def invalidate_case(db, case_id):
    """A revised bound case invalidates its step and transitive dependants."""
    linked = db.scalars(
        select(WorkflowStep).where(
            WorkflowStep.case_id == case_id, WorkflowStep.active == 1
        )
    ).all()
    for workflow_id in {s.workflow_id for s in linked}:
        w = db.get(Workflow, workflow_id)
        rows = steps(db, w)
        affected = {s.key for s in rows if s.active and s.case_id == case_id}
        for key, _, deps in SPECS[w.kind]:
            if affected.intersection(deps):
                affected.add(key)
        w.revision += 1
        for row in rows:
            if row.active and row.key in affected:
                row.active = 0
        payload = json.loads(w.payload)
        for key, tool, deps in SPECS[w.kind]:
            if key in affected:
                make_step(db, w, key, tool, deps, payload, w.revision)
        db.add(
            WorkflowEvent(
                workflow_id=w.id, revision=w.revision, event_type="case_revised"
            )
        )
