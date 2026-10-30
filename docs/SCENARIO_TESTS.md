# Scenario test coverage

## Optimization acceptance added

The current suite additionally covers actual local database migration/restore,
job lock recovery/quarantine, revision metadata, 81 concrete business outcomes,
schema/import interoperability, and all three persisted local workflow chains.
See `tests/test_ops_optimizations.py`, `test_tool_results.py`,
`test_workflow_chains.py`, `test_api_optimizations.py`, `test_contracts.py`, and
`test_review_regressions.py`. The latter contains ordinary passing tests,
not expected-failure markers. Browser checks include nested inputs, blank
numeric fields, CSV mapping, keyboard tabs/focus, DST offset input and warnings
for unsaved work across workspaces. Current evidence: [VALIDATION.md](VALIDATION.md).

The older table below describes the pure calculators specifically; its limits
do not imply that the newer local DB/worker/backup tests are unexecuted.

The following tests in `tests/test_orchestration_platform.py` execute the pure calculators with supplied synthetic inputs. `python -m unittest tests.test_orchestration_platform -v` runs them. READY in these tests means the supplied input passed that preview's checks; it does not establish that an external action happened.

| Scenario | Actual test |
| --- | --- |
| All O01–O14 and T01–T12 examples have the required result envelope and run without an exception | `test_samples` |
| Backward schedule handles branching predecessor durations and missing assumptions | `test_backward_dependencies_and_missing_duration` |
| Dependency cycles and unknown predecessors stop scheduling | `test_cycle_and_unknown_dependencies` |
| Transitive impact terminates on a cycle; unknown form conditions stay open | `test_transitive_impact_and_conditional_form` |
| Bitemporal view selects the latest known valid revision and detects equal-time conflicts | `test_bitemporal_revision_selection` |
| Missing scope, stale approval, unknown action and unsafe predicates do not grant authority | `test_authority_and_stale_approval`, `test_rule_and_document_injection_rejected`, `test_complete_manifest_and_incomplete_inputs` |
| Ambiguous external execution remains UNKNOWN and is not blindly retried | `test_ambiguous_execution_never_retry` |
| Manifest mismatch, missing/extra entries and empty manifest cannot pass; verification needs independent evidence | `test_bad_manifest_and_unverified_result`, `test_complete_manifest_and_incomplete_inputs` |
| Zero tests, skipped tests and failed tests do not approve rollout | `test_zero_skipped_failed_tests` |

These unit tests do not establish database persistence, atomic outbox/idempotency or lease behavior across processes, actual timers after restart, independent target-system readback, external adapter permissions or integration probes, document delivery, production access enforcement, backup creation or restoration, or real rollout/shadow operation. Those require separately authorized integration and operational tests with actual evidence; the tools only assess supplied data or create previews.
