"""Executable review findings; these are OPEN defects, not passing acceptance.

Strict expected failures reference docs/REVIEW.md. Remove the marker when fixing
the associated defect. Unexpected exceptions fail normally; an unexpected pass
also fails, forcing the plan and marker to be updated.
"""
from copy import deepcopy
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest
from test_core import client  # isolated API/DB fixture
from app import backup
from app.domains import orchestration, personnel, platform, recruiting, staffing


def gap(identifier):
    return pytest.mark.xfail(reason=f"Open review defect {identifier}: docs/REVIEW.md", strict=True, raises=AssertionError)


@gap("F01")
def test_rule_content_change_invalidates_approval():
    payload = deepcopy(platform.SAMPLES["T02"])
    assert platform.run("T02", payload)["data"]["authority"] is True
    payload["rule"]["predicate"]["value"] = "changed"
    payload["facts"]["type"] = "changed"
    assert platform.run("T02", payload)["data"].get("authority") is not True


@gap("F01")
def test_intent_payload_change_invalidates_approval():
    payload = deepcopy(platform.SAMPLES["T05"])
    assert platform.run("T05", payload)["data"]["authorized"] is True
    payload["payload"]["unapproved_value"] = "changed"
    assert platform.run("T05", payload)["data"].get("authorized") is not True


@gap("F02")
def test_consultation_evidence_is_bound_to_person_and_measure():
    payload = deepcopy(personnel.SAMPLES["P07"])
    assert personnel.run("P07", payload)["status"] == "READY"
    payload["person_id"] = "P-OTHER"
    payload["measure"] = "Andere Maßnahme"
    assert personnel.run("P07", payload)["status"] != "READY"


@gap("F03")
def test_conflicting_identifier_blocks_person_confirmation():
    payload = deepcopy(recruiting.SAMPLES["R05"])
    payload["identifiers"]["personnel_number"] = "WRONG"
    payload["candidates"][0]["identifiers"]["personnel_number"] = "RIGHT"
    result = recruiting.run("R05", payload)
    assert result["status"] != "READY" and not result["data"].get("confirmed_person")


@gap("F04")
def test_source_replay_does_not_cross_subject_identity(client):
    request = {"title": "Synthetisch", "payload": {"value": 1}, "source_ref": "same-source", "subject_id": "P1"}
    assert client.post("/api/tools/T1/cases", json=request).status_code == 200
    request["subject_id"] = "P2"
    assert client.post("/api/tools/T1/cases", json=request).status_code == 409


@gap("F05")
def test_hr_handoff_does_not_accept_undeclared_salary_field():
    payload = deepcopy(recruiting.SAMPLES["R06"])
    payload["approved_fields"] = {"salary": "999999"}
    assert recruiting.run("R06", payload)["status"] != "READY"


@gap("F06")
def test_staffing_order_rejects_negative_values_even_with_hash():
    payload = deepcopy(staffing.SAMPLES["A03"])
    payload.update(hours="-160", rate="-35.50")
    payload["approval"] = {"by": "synthetic-reviewer", "scope_hash": personnel.digest(payload)}
    assert staffing.run("A03", payload)["status"] != "READY"


@gap("F06")
def test_return_from_leave_rejects_negative_hours_even_with_hash():
    payload = deepcopy(personnel.SAMPLES["P10"])
    payload["hours"] = "-20"
    scope = {key: payload[key] for key in ("person_id", "return_date", "hours", "role")}
    payload["approval"] = {"by": "synthetic-reviewer", "scope_hash": personnel.digest(scope)}
    assert personnel.run("P10", payload)["status"] != "READY"


@gap("F07")
def test_distinct_event_occurrences_do_not_share_task_key():
    first = deepcopy(orchestration.SAMPLES["O01"])
    second = deepcopy(first)
    second["event"]["date"] = "2028-06-30"
    before = orchestration.run("O01", first)["data"]["tasks"][0]["key"]
    after = orchestration.run("O01", second)["data"]["tasks"][0]["key"]
    assert before != after


@gap("F08")
def test_measured_metrics_reject_negative_duration():
    payload = deepcopy(orchestration.SAMPLES["O14"])
    payload["cases"][0]["duration_days"] = -100
    assert orchestration.run("O14", payload)["status"] != "READY"


@gap("F09")
def test_backup_rejects_an_empty_non_toolbox_database(tmp_path):
    empty = tmp_path / "empty.db"
    empty.touch()
    rejected = False
    try:
        backup.create(empty, tmp_path / "snapshot")
    except backup.BackupError:
        rejected = True
    assert rejected


@gap("F11")
def test_database_file_is_private_under_permissive_umask(tmp_path):
    target = tmp_path / "review.db"
    subprocess.run(
        [sys.executable, "-c", "import os; os.umask(0o022); from app.db import init_db; init_db()"],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "TOOLBOX_DATABASE_URL": f"sqlite:///{target}"}, check=True,
    )
    assert stat.S_IMODE(target.stat().st_mode) & 0o077 == 0


@gap("F13")
def test_reloaded_job_due_time_has_explicit_utc_offset(client):
    request = {"tool_id": "T1", "payload": {}, "due_at": "2030-01-01T14:00:00+02:00"}
    assert client.post("/api/jobs", json=request).status_code == 200
    due = client.get("/api/jobs").json()[0]["due_at"]
    assert due.endswith("Z") or due.endswith("+00:00")
