"""Local SQLite snapshot, verification and restore for the single-user pilot."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from .migrations import APPLICATION_ID, SCHEMA_VERSION, validate_schema


class BackupError(Exception):
    pass


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _connect_readonly(path, immutable=False):
    uri = path.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)


def _check_database(path):
    with _connect_readonly(path, immutable=True) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise BackupError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BackupError("SQLite foreign key check failed")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        if app_id != (APPLICATION_ID if version else 0):
            raise BackupError("Invalid application identity")
        try:
            validate_schema(db, version)
        except ValueError as exc:
            raise BackupError(str(exc)) from exc
        return version


def _manifest(directory):
    with (directory / "manifest.json").open("r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if (
        not isinstance(manifest, dict)
        or (
            manifest.get("manifest_format_version", manifest.get("schema_version")) != 1
        )
        or manifest.get("db") != "backup.db"
        or not isinstance(manifest.get("sha256"), str)
        or len(manifest["sha256"]) != 64
        or not isinstance(manifest.get("created_at"), str)
    ):
        raise BackupError("Invalid backup manifest")
    return manifest


def _verify_snapshot(snapshot, manifest):
    if _sha256(snapshot) != manifest["sha256"]:
        raise BackupError("Backup hash mismatch")
    version = _check_database(snapshot)
    if (
        "application_schema_version" in manifest
        and manifest["application_schema_version"] != version
    ):
        raise BackupError("Application schema version mismatch")
    if (
        "manifest_format_version" in manifest
        and "application_schema_version" not in manifest
    ):
        raise BackupError("Missing application schema version")


def create(database, output):
    source = Path(database)
    directory = Path(output)
    if not source.is_file():
        raise BackupError("Source database does not exist")
    # mkdir is atomic and refuses an existing directory or file.
    directory.mkdir(mode=0o700)
    try:
        snapshot = directory / "backup.db"
        with _connect_readonly(source) as live:
            with sqlite3.connect(snapshot) as dest:
                live.backup(dest)
        version = _check_database(snapshot)
        manifest = {
            "manifest_format_version": 1,
            "application_schema_version": version,
            "sha256": _sha256(snapshot),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "db": "backup.db",
        }
        with (directory / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, sort_keys=True, indent=2)
            stream.write("\n")
        return manifest
    except Exception:
        shutil.rmtree(directory)
        raise


def verify(backup):
    directory = Path(backup)
    manifest = _manifest(directory)
    _verify_snapshot(directory / "backup.db", manifest)
    return manifest


def restore(backup, output):
    directory = Path(backup)
    target = Path(output)
    if target.exists() or target.is_symlink():
        raise BackupError("Restore destination already exists")
    manifest = _manifest(directory)
    # Validate the exact copied bytes, not only the source prior to copying.
    fd, name = tempfile.mkstemp(prefix=".sqlite-restore-", dir=target.parent)
    temporary = Path(name)
    try:
        with (
            os.fdopen(fd, "wb") as dest,
            (directory / "backup.db").open("rb") as source,
        ):
            shutil.copyfileobj(source, dest, 1024 * 1024)
            dest.flush()
            os.fsync(dest.fileno())
        _verify_snapshot(temporary, manifest)
        # A hard link publishes atomically and fails if a target appears meanwhile.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lokale SQLite-Sicherung erstellen, prüfen oder wiederherstellen"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("--database", required=True)
    create_parser.add_argument("--output", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--backup", required=True)
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("--backup", required=True)
    restore_parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create(args.database, args.output)
        elif args.command == "verify":
            result = verify(args.backup)
        else:
            result = restore(args.backup, args.output)
    except (
        BackupError,
        OSError,
        sqlite3.Error,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.exit(1, f"Fehler: {exc}\n")
    print(json.dumps({"status": "OK", "manifest": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
