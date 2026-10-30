from test_core import client


def test_workflow_history_and_independent_invalidation(client):
    data = {
        "kind": "start_shift",
        "title": "Start",
        "source_ref": " event ",
        "payload": {},
    }
    first = client.post("/api/workflows", json=data)
    assert first.status_code == 200, first.text
    w = first.json()
    assert len(w["steps"]) == 4 and w["steps"][0]["status"] == "NEEDS_DATA"
    assert client.post("/api/workflows", json=data).json()["id"] == w["id"]
    changed = client.patch(
        f"/api/workflows/{w['id']}",
        json={
            "revision": 1,
            "payload": {
                "document": {
                    "template": "Hi",
                    "template_version": "1",
                    "template_approved": True,
                    "fields": {},
                }
            },
        },
    )
    assert changed.status_code == 200, changed.text
    revised = changed.json()
    assert {s["key"] for s in revised["history"]} == {"document", "commitments"}
    assert (
        next(s for s in revised["steps"] if s["key"] == "tasks")["id"]
        == next(s for s in w["steps"] if s["key"] == "tasks")["id"]
    )
    assert revised["metrics"]["corrections"] == 1
    assert (
        client.patch(
            f"/api/workflows/{w['id']}", json={"revision": 1, "payload": {}}
        ).status_code
        == 409
    )


def test_unknown_steps_and_unmatched_case(client):
    assert (
        client.post(
            "/api/workflows",
            json={"kind": "hours_change", "title": "x", "payload": {"unknown": {}}},
        ).status_code
        == 422
    )
    w = client.post(
        "/api/workflows", json={"kind": "hours_change", "title": "x", "payload": {}}
    ).json()
    assert (
        client.post(
            f"/api/workflows/{w['id']}/steps/{w['steps'][0]['id']}/attach",
            json={"revision": 1, "case_id": 123},
        ).status_code
        == 409
    )


def test_attested_step_is_preserved_and_invalidated_by_case_edit(client, monkeypatch):
    from app import services
    from app.domains.orchestration import SAMPLES
    from copy import deepcopy

    # The core fixture uses a synthetic catalog; use the real calculator here.
    monkeypatch.setattr(services, "catalog", lambda: [{"id": "O01"}])
    monkeypatch.setattr(
        services,
        "evaluate",
        lambda tool, data: __import__(
            "app.domains.orchestration", fromlist=["run"]
        ).run(tool, data),
    )
    data = deepcopy(SAMPLES["O01"])
    w = client.post(
        "/api/workflows",
        json={"kind": "start_shift", "title": "Eintritt", "payload": {"event": data}},
    ).json()
    case = client.post(
        "/api/tools/O01/cases", json={"title": "Ereignis", "payload": data}
    ).json()
    path = f"/api/cases/{case['id']}"
    assert client.post(path + "/approve", json={"revision": 1}).status_code == 200
    assert (
        client.post(
            path + "/evidence",
            json={
                "revision": 1,
                "kind": "independent_readback",
                "reference": "manual:source",
                "observed": case["expected_observation"],
            },
        ).status_code
        == 200
    )
    assert client.post(path + "/complete", json={"revision": 1}).status_code == 200
    step = w["steps"][0]
    attached = client.post(
        f"/api/workflows/{w['id']}/steps/{step['id']}/attach",
        json={"revision": 1, "case_id": case["id"]},
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["steps"][0]["status"] == "COMPLETED"
    data["event"]["date"] = "2027-07-01"
    assert client.patch(path, json={"revision": 1, "payload": data}).status_code == 200
    after = client.get(f"/api/workflows/{w['id']}").json()
    assert after["revision"] == 2
    assert {x["key"] for x in after["history"]} == {
        "event",
        "tasks",
        "document",
        "commitments",
    }
    assert (
        next(x for x in after["history"] if x["key"] == "event")["status"]
        == "COMPLETED"
    )
    assert after["steps"][0]["status"] != "COMPLETED"


def test_draft_fields_match_exactly():
    import pytest
    from fastapi import HTTPException
    from types import SimpleNamespace
    from app.workflows import check_consistency

    w = SimpleNamespace(kind="hours_change")
    payload = {
        "change": {"person_id": "P1", "new": "30", "valid_from": "2026-01-01"},
        "draft": {
            "template": "{person_id} {new} {valid_from}",
            "fields": {"person_id": "P10", "new": "300", "valid_from": "2026-01-01"},
        },
    }
    with pytest.raises(HTTPException):
        check_consistency(w, "draft", payload)
    payload["draft"]["fields"].update(person_id="P1", new="30")
    check_consistency(w, "draft", payload)
