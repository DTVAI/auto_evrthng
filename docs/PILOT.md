# OP07: readiness for a controlled local pilot

The repository contains a local readiness manifest tool. It collects references
for an organizational review; it does not perform that review. A successful
`check` means only that the local manifest is complete. It does not validate
signatures, identities, approvals, tenant access, or that a referenced backup or
baseline is genuine.

## Prepare the manifest

Run from the repository root:

```sh
python -m app.pilot init --output pilot-readiness.json
python -m app.pilot check --manifest pilot-readiness.json
```

`init` creates a new file with empty fields and `status: not_ready`; it will not
overwrite a file. Fill it with references and declarations supplied by the
organization. Do not put credentials, personal records, or copied case data in
the manifest. The checker reports missing field names without echoing entered
values. Exit status is 0 for a complete local manifest, 1 for incomplete or
invalid content, and 2 when a file cannot be created/read. A complete result
still reports `organizational_signoffs_validated: false` and
`external_permissions_validated: false`.

The manifest needs all of the following before the pilot review:

- A named process owner and technical owner, each with a role and reference to
  the organization's declaration.
- References to approved templates and a specific list of allowed data fields.
- A declared role and permission set, with its declaration reference. This is
  documentation only: the local single-user application does not enforce those
  organizational roles.
- Evidence methods and retention/disposal rules for each data category.
- All three OP05 workflow pilots selected: approved hours change with draft and
  HR evidence; onboarding date shift with task and document revisions; ANÜ
  invoice discrepancy and correction run.
- A reference to a completed local backup and restore verification and a
  measured baseline for the same workflows.

The tool fixes the scope exclusions: Microsoft Graph, payroll transfer, and P13
remain excluded. Do not use a green manifest check as approval to load real data.

## Human-led pilot sequence

1. Confirm the OP01–06 integrity gates and review their current status in
   [OPTIMIZATION_STATUS.md](OPTIMIZATION_STATUS.md). A passing test suite alone
   is not a pilot authorization.
2. Have the process owner approve each template, allowed field, role, evidence
   method, retention rule, and representative workflow. Have the technical
   owner verify the local machine, database location, backup handling, and
   restore procedure. Keep the declaration references in the manifest.
3. Before using pilot data, measure a baseline for the three workflows. Record
   how active work time, waiting time, errors, and necessary human interventions
   are measured, with the period and source in the referenced record. Do not
   infer savings from examples or test fixtures.
4. Verify a local backup and restore to a new location using
   [BACKUP.md](BACKUP.md). Record the verification reference. Protect the source
   and backup because they may contain personal data.
5. Start with the smallest approved and minimized set of cases. A process owner
   reviews each result and any correction; use only data fields on the approved
   list. Keep failures, waiting, and interventions visible. Do not send or write
   results to external systems from this local pilot.
6. Compare measurements with the baseline, document open obligations, and
   review representative cases with the process owner. Re-run `check` to catch
   omissions in the manifest. The checker does not certify the review outcome.

No OP07 field pilot is represented as completed by this repository change.
Actual owner appointments, approvals, access decisions, baseline measurements,
and restore exercises must be supplied and carried out by the organization.
