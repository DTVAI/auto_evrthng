from copy import deepcopy

import pytest

from app.decisions import digest
from app.domains import orchestration, personnel, platform, recruiting, staffing


@pytest.mark.parametrize(
    "tool, fields",
    [
        (
            "T02",
            {
                "object_id": "other",
                "revision": "2",
                "action": "read",
                "scope": "other",
                "required_role": "other",
                "valid_from": "2027-02-01",
                "valid_to": "2027-11-01",
                "rule": {
                    "id": "R1",
                    "version": "1",
                    "status": "APPROVED",
                    "predicate": {"field": "type", "op": "eq", "value": "other"},
                },
            },
        ),
        (
            "T05",
            {
                "case_id": "other",
                "step": "other",
                "revision": "2",
                "target": "other",
                "payload": {"id": "other"},
                "rule_version": "2",
                "required_role": "other",
                "valid_from": "2027-02-01",
                "valid_to": "2027-11-01",
            },
        ),
    ],
)
def test_decision_scope_members_invalidate_approval(tool, fields):
    base = deepcopy(platform.SAMPLES[tool])
    assert platform.run(tool, base)["status"] == "READY"
    for key, value in fields.items():
        p = deepcopy(base)
        p[key] = value
        result = platform.run(tool, p)
        assert (
            result["data"].get("authority", result["data"].get("authorized"))
            is not True
        ), key
    for key in ("as_of", "valid_from", "valid_to"):
        p = deepcopy(base)
        p[key] = "not-a-date"
        assert platform.run(tool, p)["status"] != "READY"
    p = deepcopy(base)
    p["as_of"] = "2028-01-01"
    assert platform.run(tool, p)["status"] != "READY"


def test_consultation_scope_members():
    base = deepcopy(personnel.SAMPLES["P07"])
    assert personnel.run("P07", base)["status"] == "READY"
    for key in (
        "person_id",
        "measure",
        "draft",
        "rule_version",
        "representative",
        "consultation_scope",
    ):
        p = deepcopy(base)
        p[key] = "changed"
        assert personnel.run("P07", p)["status"] != "READY"


def test_handoff_scope_and_readback():
    base = deepcopy(recruiting.SAMPLES["R06"])
    assert recruiting.run("R06", base)["status"] == "READY"
    for key, value in {
        "identifier": "other",
        "action": "create",
        "source_id": "other",
        "approved_fields": {"name": "other"},
    }.items():
        p = deepcopy(base)
        p[key] = value
        assert recruiting.run("R06", p)["status"] != "READY"
    p = deepcopy(base)
    p.pop("observed_fields")
    result = recruiting.run("R06", p)
    assert result["data"]["prepared"] and not result["data"]["readback_confirmed"]
    assert result["status"] == "NEEDS_DECISION"
    p = deepcopy(base)
    p["approved_fields"] = {"salary": "1"}
    assert recruiting.run("R06", p)["status"] != "READY"


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True, 1.5, "", None])
def test_hours_never_bypass_validation(value):
    for module, tool in ((staffing, "A03"), (personnel, "P10")):
        p = deepcopy(module.SAMPLES[tool])
        p["hours"] = value
        p["approval"] = {"by": "HR", "scope_hash": digest({"hours": str(value)})}
        assert module.run(tool, p)["status"] != "READY"


def test_event_identity_replay_and_revision():
    p = deepcopy(orchestration.SAMPLES["O01"])
    key = orchestration.run("O01", p)["data"]["tasks"][0]["key"]
    p["existing_keys"] = [key]
    assert orchestration.run("O01", p)["data"]["tasks"][0]["existing"]
    for field, value in (
        ("event_id", "E2"),
        ("revision", 2),
        ("source", "other"),
        ("person_id", "P2"),
    ):
        changed = deepcopy(p)
        changed["event"][field] = value
        assert orchestration.run("O01", changed)["data"]["tasks"][0]["key"] != key
    del p["event"]["revision"]
    assert orchestration.run("O01", p)["status"] != "READY"


def test_metrics_closed_only_and_validation():
    base = deepcopy(orchestration.SAMPLES["O14"])
    result = orchestration.run("O14", base)
    assert result["data"]["open"] == 1 and result["data"]["closed"] == 1
    assert result["data"]["duration_sample_count"] == 1
    assert result["data"]["mean_duration_days"] == "4"
    for bad in ("NaN", "-1", True, 1.5):
        p = deepcopy(base)
        p["cases"][0]["duration_days"] = bad
        assert orchestration.run("O14", p)["status"] != "READY"
    base["cases"][1]["duration_days"] = 2
    assert orchestration.run("O14", base)["status"] != "READY"
