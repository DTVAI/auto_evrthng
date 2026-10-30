# Local SQLite backup and restore

The pilot stores cases, artifacts, pending jobs, and other application records in one SQLite database. Use the database file configured for the application; these commands operate only on local paths. The snapshot uses SQLite's backup API, so committed data in a WAL is included consistently while the application is running. The live database is not modified by this command.

```sh
python -m app.backup create --database /path/to/pilot.db --output /path/to/new-backup-directory
python -m app.backup verify --backup /path/to/new-backup-directory
python -m app.backup restore --backup /path/to/new-backup-directory --output /path/to/new-restored.db
```

Create requires a new directory and writes `backup.db` plus `manifest.json` containing the SHA-256 digest, schema version, UTC creation time and fixed database name. Create, verify and restore check SQLite integrity and foreign keys. Restore copies to a temporary file, checks the copied bytes and database, then publishes the result atomically without overwriting an existing destination. Restore to a new location and configure the application to use it after checking the result; it does not replace a live database. Each command exits nonzero on failure. Failed creation removes its newly created directory; failed restore removes its temporary file.

This is a validated local snapshot, not an encrypted backup or a production recovery certification. The database and backup can contain sensitive records; protect the directory and arrange encryption, retention, off-host copies, and periodic operational recovery exercises separately. The manifest detects accidental changes but is not authenticated: a party able to alter both the database and manifest can replace them. No environment secrets are intentionally added to the manifest, but any sensitive content already stored in the database is included. Files stored outside the database are not backed up.
