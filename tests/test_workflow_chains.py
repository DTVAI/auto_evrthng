"""Real HTTP acceptance of local chains with independent target evidence."""

import hashlib
import json
from copy import deepcopy

from test_acceptance import api


def h(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def case(api, tool, payload, observed, subject=None):
    created = ok(
        api.post(
            f"/api/tools/{tool}/cases",
            json={"title": f"Test {tool}", "payload": payload, "subject_id": subject},
        )
    )
    assert created["result"]["status"] == "READY", created["result"]
    assert created["expected_observation"] == observed
    cid = created["id"]
    ok(api.post(f"/api/cases/{cid}/approve", json={"revision": 1}))
    ok(
        api.post(
            f"/api/cases/{cid}/evidence",
            json={
                "revision": 1,
                "kind": "independent_readback",
                "reference": f"manual:{tool}",
                "observed": observed,
            },
        )
    )
    assert (
        ok(api.post(f"/api/cases/{cid}/complete", json={"revision": 1}))[
            "completion_basis"
        ]
        == "manual_attestation"
    )
    return cid


def attach(api, workflow, key, case_id, expect=200):
    step = next(s for s in workflow["steps"] if s["key"] == key)
    response = api.post(
        f"/api/workflows/{workflow['id']}/steps/{step['id']}/attach",
        json={"revision": workflow["revision"], "case_id": case_id},
    )
    assert response.status_code == expect, response.text
    return response.json()


def approved(payload, fields):
    p = deepcopy(payload)
    p["approval"] = {"by": "HR-Test", "scope_hash": h({k: p[k] for k in fields})}
    return p


def hours_inputs():
    change = {
        "person_id": "P1",
        "old": "40",
        "new": "30",
        "unit": "Stunden/Woche",
        "model": "unbefristet",
        "valid_from": "2027-06-30",
    }
    change = approved(
        change, ("person_id", "old", "new", "unit", "valid_from", "model")
    )
    draft = {
        "template": "Person {person_id}: {new} Stunden ab {valid_from}",
        "template_version": "1",
        "template_approved": True,
        "fields": {"person_id": "P1", "new": "30", "valid_from": "2027-06-30"},
    }
    hr = {
        "person_id": "P1",
        "fact_id": "hours",
        "old": "40",
        "new": "30",
        "valid_from": "2027-06-30",
        "reason": "Vereinbarung",
        "history": [{"value": "40"}],
    }
    hr = approved(hr, ("person_id", "fact_id", "old", "new", "valid_from", "reason"))
    return {"change": change, "draft": draft, "hr_record": hr}


def test_hours_change_chain_and_wrong_person(api):
    inputs = hours_inputs()
    w = ok(
        api.post(
            "/api/workflows",
            json={"kind": "hours_change", "title": "Stunden", "payload": inputs},
        )
    )
    change = {
        "person_id": "P1",
        "new": "30",
        "unit": "Stunden/Woche",
        "valid_from": "2027-06-30",
    }
    cid = case(api, "P02", inputs["change"], change, "P1")
    w = attach(api, w, "change", cid)
    draft_hash = hashlib.sha256(b"Person P1: 30 Stunden ab 2027-06-30").hexdigest()
    cid = case(api, "P05", inputs["draft"], {"document_hash": draft_hash})
    w = attach(api, w, "draft", cid)
    target = {
        "person_id": "P1",
        "fact_id": "hours",
        "new": "30",
        "valid_from": "2027-06-30",
    }
    cid = case(api, "P04", inputs["hr_record"], target, "P1")
    w = attach(api, w, "hr_record", cid)
    assert w["status"] == "COMPLETED" and w["metrics"]["steps_completed"] == 3
    # An independently completed case for another person cannot be bound.
    wrong = deepcopy(inputs)
    wrong["hr_record"]["person_id"] = "P2"
    wrong["hr_record"] = approved(
        wrong["hr_record"],
        ("person_id", "fact_id", "old", "new", "valid_from", "reason"),
    )
    bad = ok(
        api.post(
            "/api/workflows",
            json={"kind": "hours_change", "title": "Widerspruch", "payload": wrong},
        )
    )
    bad = attach(api, bad, "change", case(api, "P02", wrong["change"], change, "P1"))
    bad = attach(
        api,
        bad,
        "draft",
        case(api, "P05", wrong["draft"], {"document_hash": draft_hash}),
    )
    other = {
        "person_id": "P2",
        "fact_id": "hours",
        "new": "30",
        "valid_from": "2027-06-30",
    }
    other_id = case(api, "P04", wrong["hr_record"], other, "P2")
    attach(api, bad, "hr_record", other_id, 409)
    assert ok(api.get(f"/api/workflows/{bad['id']}"))["status"] == "OPEN"


def start_inputs():
    event = {
        "type": "start",
        "person_id": "P1",
        "date": "2027-06-30",
        "source": "HR",
        "event_id": "E1",
        "revision": 1,
    }
    rule = {
        "id": "R1",
        "version": "1",
        "status": "APPROVED",
        "trigger": "start",
        "steps": [{"id": "contract", "owner": "HR", "lead_days": 5}],
    }
    tasks = {
        "target_date": "2027-06-30",
        "tasks": [
            {"id": "contract", "duration_days": 3, "depends_on": [], "confirmed": True},
            {
                "id": "signature",
                "duration_days": 2,
                "depends_on": ["contract"],
                "confirmed": True,
            },
        ],
    }
    document = {
        "template": "Eintritt {person_id} am {date}",
        "template_version": "1",
        "template_approved": True,
        "fields": {"person_id": "P1", "date": "2027-06-30"},
    }
    commitments = {
        "commitments": [
            {
                "id": "C1",
                "owner": "HR",
                "due": "2027-06-30",
                "conditions_met": True,
                "proof": "signed:C1",
            }
        ]
    }
    return {
        "event": {"event": event, "rule": rule},
        "tasks": tasks,
        "document": document,
        "commitments": commitments,
    }


def test_start_shift_chain_and_wrong_date(api):
    p = start_inputs()
    w = ok(
        api.post(
            "/api/workflows",
            json={"kind": "start_shift", "title": "Eintritt", "payload": p},
        )
    )
    taskkey = h(
        {
            "source": "HR",
            "event_id": "E1",
            "event_date": "2027-06-30",
            "person_id": "P1",
            "revision": 1,
            "rule_id": "R1",
            "rule_version": "1",
            "step_id": "contract",
        }
    )
    target = {
        "event": {
            "person_id": "P1",
            "date": "2027-06-30",
            "source": "HR",
            "event_id": "E1",
            "revision": 1,
        },
        "tasks": [
            {
                "id": "contract",
                "key": taskkey,
                "existing": False,
                "due": "2027-06-25",
                "owner": "HR",
                "depends_on": [],
                "reason": "R1",
            }
        ],
    }
    w = attach(api, w, "event", case(api, "O01", p["event"], target, "P1"))
    schedule = {
        "target_date": "2027-06-30",
        "schedule": [
            {
                "id": "contract",
                "start": "2027-06-25",
                "end": "2027-06-28",
                "assumption": False,
            },
            {
                "id": "signature",
                "start": "2027-06-28",
                "end": "2027-06-30",
                "assumption": False,
            },
        ],
    }
    w = attach(api, w, "tasks", case(api, "O02", p["tasks"], schedule))
    draft_hash = hashlib.sha256(b"Eintritt P1 am 2027-06-30").hexdigest()
    w = attach(
        api,
        w,
        "document",
        case(api, "P05", p["document"], {"document_hash": draft_hash}),
    )
    w = attach(
        api,
        w,
        "commitments",
        case(
            api,
            "O13",
            p["commitments"],
            {"commitments": p["commitments"]["commitments"]},
        ),
    )
    assert w["status"] == "COMPLETED"
    wrong = deepcopy(p)
    wrong["document"]["fields"]["date"] = "2027-07-01"
    revised = ok(
        api.patch(f"/api/workflows/{w['id']}", json={"revision": 1, "payload": wrong})
    )
    assert {s["key"] for s in revised["history"]} == {"document", "commitments"}
    assert {s["key"] for s in revised["steps"] if s["status"] == "COMPLETED"} == {
        "event",
        "tasks",
    }
    wrong_hash = hashlib.sha256(b"Eintritt P1 am 2027-07-01").hexdigest()
    cid = case(api, "P05", wrong["document"], {"document_hash": wrong_hash})
    attach(api, revised, "document", cid, 409)


def test_staffing_invoice_dispute_and_corrected_revision(api):
    hours = {
        "person_id": "P1",
        "start": "2027-06-01",
        "end": "2027-06-30",
        "supplier_lines": [
            {"id": "L1", "date": "2027-06-02", "hours": "8", "approved": True},
            {"id": "L2", "date": "2027-06-03", "hours": "6", "approved": True},
        ],
        "time_lines": [
            {"id": "L1", "date": "2027-06-02", "hours": "8"},
            {"id": "L2", "date": "2027-06-03", "hours": "6"},
        ],
    }
    invoice = {
        "supplier": "S1",
        "invoice_number": "INV1",
        "order_revision": "1",
        "invoice_lines": [
            {"id": "L1", "hours": "8", "rate": "35.00", "amount": "280.00"},
            {"id": "L2", "hours": "7", "rate": "35.00", "amount": "245.00"},
        ],
        "confirmed_lines": [
            {"id": "L1", "hours": "8", "rate": "35.00"},
            {"id": "L2", "hours": "6", "rate": "35.00"},
        ],
        "existing_invoices": [],
    }
    correction = {
        "dispute_id": "D1",
        "reason": "Stundenabweichung L2",
        "line_ids": ["L2"],
        "invoice_number": "INV1",
        "correction_route": "Rechnungskorrektur",
        "recipient": "S1",
        "status": "resolved",
        "resolution_evidence": "corrected:INV1",
    }
    p = {"hours": hours, "invoice": invoice, "correction": correction}
    w = ok(
        api.post(
            "/api/workflows",
            json={"kind": "staffing_invoice", "title": "Rechnung", "payload": p},
        )
    )
    observed_hours = {
        "person_id": "P1",
        "start": "2027-06-01",
        "end": "2027-06-30",
        "time_lines": hours["time_lines"],
    }
    hours_case = case(api, "A05", hours, observed_hours, "P1")
    w = attach(api, w, "hours", hours_case)
    discrepant = next(s for s in w["steps"] if s["key"] == "invoice")
    assert discrepant["result"]["status"] == "NEEDS_DECISION"
    assert discrepant["result"]["data"]["lines"] == [
        {"id": "L1", "issues": [], "expected_amount": "280.00"},
        {"id": "L2", "issues": ["Stunden weichen ab"], "expected_amount": "210.00"},
    ]
    open_case = ok(
        api.post(
            "/api/tools/A06/cases", json={"title": "Abweichung", "payload": invoice}
        )
    )
    assert (
        api.post(
            f"/api/cases/{open_case['id']}/complete", json={"revision": 1}
        ).status_code
        == 409
    )
    correction_target = {
        "dispute_id": "D1",
        "invoice_number": "INV1",
        "line_ids": ["L2"],
        "status": "resolved",
    }
    correction_case = case(api, "A07", correction, correction_target)
    w = attach(api, w, "correction", correction_case)
    assert w["status"] == "OPEN" and {
        s["key"] for s in w["steps"] if s["status"] == "COMPLETED"
    } == {"hours", "correction"}
    old_hours = next(s for s in w["steps"] if s["key"] == "hours")["id"]
    corrected = deepcopy(p)
    corrected["invoice"]["invoice_lines"][1].update(hours="6", amount="210.00")
    w = ok(
        api.patch(
            f"/api/workflows/{w['id']}", json={"revision": 1, "payload": corrected}
        )
    )
    assert next(s for s in w["steps"] if s["key"] == "hours")["id"] == old_hours
    assert {s["key"] for s in w["history"]} == {"invoice", "correction"}
    assert (
        next(s for s in w["history"] if s["key"] == "correction")["status"]
        == "COMPLETED"
    )
    target = {
        "supplier": "S1",
        "invoice_number": "INV1",
        "order_revision": "1",
        "invoice_lines": corrected["invoice"]["invoice_lines"],
    }
    w = attach(api, w, "invoice", case(api, "A06", corrected["invoice"], target))
    w = attach(api, w, "correction", correction_case)
    assert w["status"] == "COMPLETED" and w["metrics"]["steps_completed"] == 3
    assert w["metrics"]["corrections"] == 1
