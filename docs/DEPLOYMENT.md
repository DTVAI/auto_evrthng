# Deployment boundary: local pilot and later options

## Available now

The application runs as a local, single-user pilot with SQLite. Start it using
the repository's [README instructions](../README.md). The pilot readiness
manifest in [PILOT.md](PILOT.md) helps collect evidence for a human gate. Local
backup commands are documented in [BACKUP.md](BACKUP.md); they verify a SQLite
copy and restore but do not provide encryption, off-host retention, or an
operational recovery service.

Before any real pilot, the organization must supply and verify named process
and technical owners, approved templates and data fields, role/permission
declarations, evidence and category retention rules, a representative baseline,
and a completed restore exercise. The organization must decide which records
may be used and secure the host, database, and backups. Entered roles are not
authentication or access control. Local readiness output cannot prove those
conditions.

This deployment has no organizational identity provider, enforced multi-user
RBAC, production PostgreSQL migrations, or live HRworks connection. It does not
send email or change external records. Microsoft Graph, payroll transfer, and
P13 are excluded.

## Later work, only after need is confirmed

OP08 is conditional. A confirmed multi-user need would require a PostgreSQL
design and tested migrations, server-side identity integration, and enforced
authorization on searches, derived views, downloads, and exports. Decision
roles must be distinct and auditable. Access removal must take effect across
those paths. The deployment owner must also specify monitoring, encrypted and
off-host backups, retention, recovery objectives, and repeated restore tests.

An HRworks adapter is a separate, conditional path. First document the exact
read-only capability needed and obtain the appropriate tenant-level permission
from the system owner. Prove the read and manual readback behavior with
representative data. Any later write operation requires separately granted
tenant rights, idempotency, and independent readback; timeout outcomes must
remain unknown until reconciled. Store any credentials only in secure runtime
configuration after that integration exists and its need is approved. No login,
token, tenant access, or secret is requested or configured by this project.

Outlook COM may be considered separately for Windows. File/EML import remains
the independent local path. No Graph fallback or payroll integration is part
of the deployment roadmap.

## Requirements this code cannot satisfy

The following require organizational decisions, external system owners, or
operational infrastructure:

- Appointing process and technical owners and approving templates, fields,
  role assignments, evidence methods, retention periods, and pilot data.
- Granting and verifying tenant permissions, identity-provider configuration,
  HRworks capability access, or any later external write authorization.
- Producing real baseline measurements and carrying out witnessed pilot case
  reviews and repeatable recovery exercises.
- Provisioning PostgreSQL, migration and rollback procedures, identity/RBAC
  infrastructure, encryption keys, protected backup storage, monitoring, and
  operating procedures.

The readiness CLI records references to these decisions; it cannot create or
authenticate them.
