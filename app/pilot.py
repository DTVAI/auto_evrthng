"""Create and locally check the documentation gates for an OP07 pilot.

This module checks whether a manifest has the fields needed for a human-led
pilot review. It cannot authenticate the references or attest organizational
approval, identity, or tenant permissions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKFLOWS = {
    "hours_change": "Approved hours change with draft and HR evidence",
    "start_shift": "Onboarding date shift with task and document revisions",
    "staffing_invoice": "Staffing invoice discrepancy and correction run",
}
EXCLUSIONS = {
    "microsoft_graph": "permanently_excluded",
    "payroll_transfer": "permanently_excluded",
    "p13": "permanently_excluded",
}


def empty_manifest() -> dict[str, Any]:
    """Return a safe, explicitly incomplete OP07 manifest template."""
    return {
        "schema_version": 1,
        "status": "not_ready",
        "scope_exclusions": dict(EXCLUSIONS),
        "process_owner": {"name": "", "role": "", "declaration_ref": ""},
        "technical_owner": {"name": "", "role": "", "declaration_ref": ""},
        "approved_template_refs": [],
        "allowed_data_fields": [],
        "roles_permissions": [],
        "evidence_methods": [],
        "category_retention_rules": [],
        "selected_workflow_pilots": [
            {"id": workflow_id, "selected": False} for workflow_id in WORKFLOWS
        ],
        "backup_restore_verification_ref": "",
        "measured_baseline_ref": "",
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_nonempty(item) for item in value)
    )


def _check_manifest(data: Any) -> list[str]:
    """Return missing or malformed gate names without echoing user values."""
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    required_keys = set(empty_manifest())
    for key in sorted(required_keys - data.keys()):
        issues.append(f"missing field: {key}")
    extra = data.keys() - required_keys
    for key in sorted(extra):
        issues.append(f"unexpected field: {key}")
    if data.get("schema_version") != 1:
        issues.append("schema_version must be 1")
    if data.get("status") != "not_ready":
        issues.append(
            "status must remain not_ready; readiness is computed by this check"
        )
    if data.get("scope_exclusions") != EXCLUSIONS:
        issues.append(
            "scope_exclusions must keep Graph, payroll transfer, and P13 excluded"
        )

    for owner in ("process_owner", "technical_owner"):
        record = data.get(owner)
        if not isinstance(record, dict) or any(
            not _nonempty(record.get(key))
            for key in ("name", "role", "declaration_ref")
        ):
            issues.append(f"{owner} requires name, role, and declaration_ref")

    if not _list_of_strings(data.get("approved_template_refs")):
        issues.append(
            "approved_template_refs requires at least one non-empty reference"
        )
    if not _list_of_strings(data.get("allowed_data_fields")):
        issues.append("allowed_data_fields requires at least one declared field")

    roles = data.get("roles_permissions")
    if (
        not isinstance(roles, list)
        or not roles
        or any(
            not isinstance(item, dict)
            or any(
                not _nonempty(item.get(key))
                for key in ("role", "permissions", "declaration_ref")
            )
            for item in roles
        )
    ):
        issues.append(
            "roles_permissions requires role, permissions, and declaration_ref for each role"
        )

    evidence = data.get("evidence_methods")
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(
            not isinstance(item, dict)
            or any(not _nonempty(item.get(key)) for key in ("method", "evidence_ref"))
            for item in evidence
        )
    ):
        issues.append(
            "evidence_methods requires method and evidence_ref for each method"
        )

    retention = data.get("category_retention_rules")
    if (
        not isinstance(retention, list)
        or not retention
        or any(
            not isinstance(item, dict)
            or any(
                not _nonempty(item.get(key))
                for key in (
                    "category",
                    "retention_period",
                    "disposal_method",
                    "declaration_ref",
                )
            )
            for item in retention
        )
    ):
        issues.append(
            "category_retention_rules requires category, period, disposal, and declaration_ref"
        )

    pilots = data.get("selected_workflow_pilots")
    selected = (
        {
            item.get("id")
            for item in pilots
            if isinstance(item, dict) and item.get("selected") is True
        }
        if isinstance(pilots, list)
        else set()
    )
    declared = (
        {item.get("id") for item in pilots if isinstance(item, dict)}
        if isinstance(pilots, list)
        else set()
    )
    if (
        not isinstance(pilots, list)
        or len(pilots) != len(WORKFLOWS)
        or declared != set(WORKFLOWS)
        or selected != set(WORKFLOWS)
    ):
        issues.append(
            "selected_workflow_pilots must select exactly the three declared OP05 workflows"
        )

    for key in ("backup_restore_verification_ref", "measured_baseline_ref"):
        if not _nonempty(data.get(key)):
            issues.append(f"{key} is required")
    return issues


def _emit_report(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        report = {
            "local_manifest_complete": False,
            "missing_gates": ["manifest could not be read as valid JSON"],
            "organizational_signoffs_validated": False,
            "external_permissions_validated": False,
        }
        print(json.dumps(report, indent=2))
        return 2

    issues = _check_manifest(data)
    report = {
        "local_manifest_complete": not issues,
        "missing_gates": issues,
        "organizational_signoffs_validated": False,
        "external_permissions_validated": False,
        "scope_exclusions": dict(EXCLUSIONS),
    }
    print(json.dumps(report, indent=2))
    return 0 if not issues else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or locally check OP07 pilot readiness evidence."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init", help="write an empty, not-ready manifest")
    init_parser.add_argument("--output", required=True, type=Path)
    check_parser = commands.add_parser("check", help="check manifest completeness")
    check_parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)

    if args.command == "init":
        try:
            with args.output.open("x", encoding="utf-8") as output:
                json.dump(empty_manifest(), output, indent=2)
                output.write("\n")
        except FileExistsError:
            print("output already exists; choose a new path", file=sys.stderr)
            return 2
        except OSError:
            print("could not create output file", file=sys.stderr)
            return 2
        print(
            "Created not-ready pilot manifest. No approval or permission was validated."
        )
        return 0
    return _emit_report(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
