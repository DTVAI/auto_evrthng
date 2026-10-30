import json

from app.pilot import EXCLUSIONS, WORKFLOWS, _check_manifest, empty_manifest, main


def test_pilot_ids_match_the_implemented_workflow_contract():
    from app.workflows import SPECS

    assert (
        set(WORKFLOWS)
        == set(SPECS)
        == {"hours_change", "start_shift", "staffing_invoice"}
    )


def complete_synthetic_manifest():
    manifest = empty_manifest()
    manifest.update(
        {
            "process_owner": {
                "name": "Example Process Owner",
                "role": "process",
                "declaration_ref": "synthetic://owner",
            },
            "technical_owner": {
                "name": "Example Technical Owner",
                "role": "operations",
                "declaration_ref": "synthetic://technical",
            },
            "approved_template_refs": ["synthetic://template-v1"],
            "allowed_data_fields": ["case_id", "effective_date"],
            "roles_permissions": [
                {
                    "role": "reviewer",
                    "permissions": "review local draft",
                    "declaration_ref": "synthetic://roles",
                }
            ],
            "evidence_methods": [
                {
                    "method": "manual review record",
                    "evidence_ref": "synthetic://evidence",
                }
            ],
            "category_retention_rules": [
                {
                    "category": "synthetic case data",
                    "retention_period": "30 days after pilot close",
                    "disposal_method": "verified local deletion",
                    "declaration_ref": "synthetic://retention",
                }
            ],
            "selected_workflow_pilots": [
                {"id": workflow_id, "selected": True} for workflow_id in WORKFLOWS
            ],
            "backup_restore_verification_ref": "synthetic://restore-check",
            "measured_baseline_ref": "synthetic://baseline",
        }
    )
    return manifest


def test_empty_manifest_is_explicitly_not_ready_and_has_all_missing_gates():
    manifest = empty_manifest()
    issues = _check_manifest(manifest)

    assert manifest["status"] == "not_ready"
    assert not manifest["scope_exclusions"]["microsoft_graph"] == "included"
    assert "process_owner requires name, role, and declaration_ref" in issues
    assert "measured_baseline_ref is required" in issues
    assert (
        "selected_workflow_pilots must select exactly the three declared OP05 workflows"
        in issues
    )


def test_complete_synthetic_manifest_passes_local_completeness_only():
    assert _check_manifest(complete_synthetic_manifest()) == []


def test_check_cli_does_not_claim_to_validate_signoffs_or_external_permissions(
    tmp_path, capsys
):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(complete_synthetic_manifest()), encoding="utf-8")

    assert main(["check", "--manifest", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["local_manifest_complete"] is True
    assert report["organizational_signoffs_validated"] is False
    assert report["external_permissions_validated"] is False
    assert report["scope_exclusions"] == EXCLUSIONS


def test_graph_payroll_and_p13_cannot_be_enabled(tmp_path, capsys):
    for excluded_scope in EXCLUSIONS:
        manifest = complete_synthetic_manifest()
        manifest["scope_exclusions"][excluded_scope] = "included"
        path = tmp_path / f"{excluded_scope}.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")

        assert main(["check", "--manifest", str(path)]) == 1
        report = json.loads(capsys.readouterr().out)
        assert report["local_manifest_complete"] is False
        assert any("scope_exclusions" in issue for issue in report["missing_gates"])


def test_manifest_rejects_unexpected_fields_and_unselected_workflow():
    manifest = complete_synthetic_manifest()
    manifest["credential"] = "must not be a manifest field"
    manifest["selected_workflow_pilots"][0]["selected"] = False

    issues = _check_manifest(manifest)
    assert "unexpected field: credential" in issues
    assert any("selected_workflow_pilots" in issue for issue in issues)
