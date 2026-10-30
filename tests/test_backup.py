import json
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "live.db"
        self.backup = self.root / "backup"
        env = dict(os.environ, TOOLBOX_DATABASE_URL=f"sqlite:///{self.database}")
        subprocess.run(
            [sys.executable, "-c", "from app.db import init_db; init_db()"],
            env=env,
            check=True,
        )
        self.db = sqlite3.connect(self.database)
        self.addCleanup(self.db.close)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            INSERT INTO cases VALUES (1, 'O01', 'Case', NULL, 'source', '{}', 'hash', 1, 'OPEN', '{}', '2027-01-01', '2027-01-01');
            INSERT INTO test_runs VALUES (1, 'O01', 1, 'READY', '{}', '2027-01-01');
            INSERT INTO artifacts VALUES (1, 1, 1, 'draft.txt', 'text/plain', 'Document content');
            INSERT INTO jobs VALUES (1, 'O01', '{}', 'PENDING', '2027-01-01', NULL, NULL, 0, NULL, '2027-01-01');
        """)
        self.db.commit()

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "app.backup", *map(str, args)],
            capture_output=True,
            text=True,
        )

    def test_wal_snapshot_and_restore(self):
        # Keep connection open so committed WAL data is present during snapshot.
        self.assertEqual(
            self.cli(
                "create", "--database", self.database, "--output", self.backup
            ).returncode,
            0,
        )
        self.assertEqual(self.cli("verify", "--backup", self.backup).returncode, 0)
        restored = self.root / "restored.db"
        self.assertEqual(
            self.cli(
                "restore", "--backup", self.backup, "--output", restored
            ).returncode,
            0,
        )
        with sqlite3.connect(restored) as db:
            self.assertEqual(
                db.execute("SELECT title FROM cases").fetchone(), ("Case",)
            )
            self.assertEqual(
                db.execute("SELECT content FROM artifacts").fetchone(),
                ("Document content",),
            )
            self.assertEqual(
                db.execute("SELECT status FROM jobs").fetchone(), ("PENDING",)
            )
        manifest = json.loads((self.backup / "manifest.json").read_text())
        self.assertEqual(
            set(manifest),
            {
                "manifest_format_version",
                "application_schema_version",
                "sha256",
                "created_at",
                "db",
            },
        )

    def test_empty_or_wrong_database_is_rejected(self):
        wrong = self.root / "wrong.db"
        with sqlite3.connect(wrong) as db:
            db.execute("CREATE TABLE unrelated (id INTEGER)")
        self.assertNotEqual(
            self.cli("create", "--database", wrong, "--output", self.backup).returncode,
            0,
        )
        self.assertFalse(self.backup.exists())
        empty = self.root / "empty.db"
        sqlite3.connect(empty).close()
        self.assertNotEqual(
            self.cli("create", "--database", empty, "--output", self.backup).returncode,
            0,
        )
        self.assertFalse(self.backup.exists())

    def test_forged_column_only_schema_fails_create_verify_and_restore(self):
        from app.db import Base
        from app import models, workflow_models  # noqa: F401
        from app.migrations import APPLICATION_ID, SCHEMA_VERSION

        fake = self.root / "fake.db"
        with sqlite3.connect(fake) as db:
            for table in Base.metadata.sorted_tables:
                columns = ", ".join(f'"{column.name}" TEXT' for column in table.columns)
                db.execute(f'CREATE TABLE "{table.name}" ({columns})')
            db.execute(
                "CREATE UNIQUE INDEX fake_revision ON revisions(case_id, revision)"
            )
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.assertNotEqual(
            self.cli("create", "--database", fake, "--output", self.backup).returncode,
            0,
        )
        self.backup.mkdir()
        snapshot = self.backup / "backup.db"
        snapshot.write_bytes(fake.read_bytes())
        manifest = {
            "manifest_format_version": 1,
            "application_schema_version": SCHEMA_VERSION,
            "db": "backup.db",
            "created_at": "2026-01-01T00:00:00Z",
            "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        }
        (self.backup / "manifest.json").write_text(json.dumps(manifest))
        self.assertNotEqual(self.cli("verify", "--backup", self.backup).returncode, 0)
        output = self.root / "fake-restored.db"
        self.assertNotEqual(
            self.cli("restore", "--backup", self.backup, "--output", output).returncode,
            0,
        )
        self.assertFalse(output.exists())

    def test_tampering_fails_verify_and_restore(self):
        self.assertEqual(
            self.cli(
                "create", "--database", self.database, "--output", self.backup
            ).returncode,
            0,
        )
        with (self.backup / "backup.db").open("ab") as f:
            f.write(b"tamper")
        self.assertNotEqual(self.cli("verify", "--backup", self.backup).returncode, 0)
        output = self.root / "restore.db"
        self.assertNotEqual(
            self.cli("restore", "--backup", self.backup, "--output", output).returncode,
            0,
        )
        self.assertFalse(output.exists())

    def test_refuses_overwrite(self):
        self.backup.mkdir()
        marker = self.backup / "marker"
        marker.write_text("untouched")
        self.assertNotEqual(
            self.cli(
                "create", "--database", self.database, "--output", self.backup
            ).returncode,
            0,
        )
        self.assertEqual(marker.read_text(), "untouched")
        marker.unlink()
        self.backup.rmdir()
        self.assertEqual(
            self.cli(
                "create", "--database", self.database, "--output", self.backup
            ).returncode,
            0,
        )
        output = self.root / "existing.db"
        output.write_text("untouched")
        self.assertNotEqual(
            self.cli("restore", "--backup", self.backup, "--output", output).returncode,
            0,
        )
        self.assertEqual(output.read_text(), "untouched")

    def test_foreign_key_violations_rejected(self):
        self.db.execute("PRAGMA foreign_keys=OFF")
        self.db.execute(
            "INSERT INTO artifacts VALUES (2, 1, 999, 'orphan', 'text/plain', 'orphan')"
        )
        self.db.commit()
        self.assertNotEqual(
            self.cli(
                "create", "--database", self.database, "--output", self.backup
            ).returncode,
            0,
        )
        self.assertFalse(self.backup.exists())


if __name__ == "__main__":
    unittest.main()
