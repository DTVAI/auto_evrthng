import json
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
        self.database = self.root / 'live.db'
        self.backup = self.root / 'backup'
        self.db = sqlite3.connect(self.database)
        self.addCleanup(self.db.close)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE cases (id INTEGER PRIMARY KEY, tool_id TEXT NOT NULL, title TEXT NOT NULL, subject_id TEXT, source_ref TEXT, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE test_runs (id INTEGER PRIMARY KEY, tool_id TEXT NOT NULL, case_id INTEGER REFERENCES cases(id), status TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE artifacts (id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES test_runs(id), case_id INTEGER REFERENCES cases(id), name TEXT NOT NULL, media_type TEXT NOT NULL, content TEXT NOT NULL);
            CREATE TABLE jobs (id INTEGER PRIMARY KEY, tool_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, due_at TEXT NOT NULL, lease_until TEXT, lease_token TEXT, attempts INTEGER NOT NULL, run_id INTEGER REFERENCES test_runs(id), created_at TEXT NOT NULL);
            INSERT INTO cases VALUES (1, 'O01', 'Case', NULL, 'source', '{}', 'hash', 1, 'OPEN', '{}', '2027-01-01', '2027-01-01');
            INSERT INTO test_runs VALUES (1, 'O01', 1, 'READY', '{}', '2027-01-01');
            INSERT INTO artifacts VALUES (1, 1, 1, 'draft.txt', 'text/plain', 'Document content');
            INSERT INTO jobs VALUES (1, 'O01', '{}', 'PENDING', '2027-01-01', NULL, NULL, 0, NULL, '2027-01-01');
        ''')
        self.db.commit()

    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'app.backup', *map(str,args)], capture_output=True, text=True)

    def test_wal_snapshot_and_restore(self):
        # Keep connection open so committed WAL data is present during snapshot.
        self.assertEqual(self.cli('create','--database',self.database,'--output',self.backup).returncode, 0)
        self.assertEqual(self.cli('verify','--backup',self.backup).returncode, 0)
        restored=self.root/'restored.db'
        self.assertEqual(self.cli('restore','--backup',self.backup,'--output',restored).returncode, 0)
        with sqlite3.connect(restored) as db:
            self.assertEqual(db.execute('SELECT title FROM cases').fetchone(), ('Case',))
            self.assertEqual(db.execute('SELECT content FROM artifacts').fetchone(), ('Document content',))
            self.assertEqual(db.execute('SELECT status FROM jobs').fetchone(), ('PENDING',))
        manifest=json.loads((self.backup/'manifest.json').read_text())
        self.assertEqual(set(manifest), {'schema_version','sha256','created_at','db'})

    def test_tampering_fails_verify_and_restore(self):
        self.assertEqual(self.cli('create','--database',self.database,'--output',self.backup).returncode, 0)
        with (self.backup/'backup.db').open('ab') as f: f.write(b'tamper')
        self.assertNotEqual(self.cli('verify','--backup',self.backup).returncode, 0)
        output=self.root/'restore.db'
        self.assertNotEqual(self.cli('restore','--backup',self.backup,'--output',output).returncode, 0)
        self.assertFalse(output.exists())

    def test_refuses_overwrite(self):
        self.backup.mkdir()
        marker=self.backup/'marker'; marker.write_text('untouched')
        self.assertNotEqual(self.cli('create','--database',self.database,'--output',self.backup).returncode, 0)
        self.assertEqual(marker.read_text(),'untouched')
        marker.unlink()
        self.backup.rmdir()
        self.assertEqual(self.cli('create','--database',self.database,'--output',self.backup).returncode, 0)
        output=self.root/'existing.db'; output.write_text('untouched')
        self.assertNotEqual(self.cli('restore','--backup',self.backup,'--output',output).returncode, 0)
        self.assertEqual(output.read_text(),'untouched')

    def test_foreign_key_violations_rejected(self):
        self.db.execute('PRAGMA foreign_keys=OFF')
        self.db.execute("INSERT INTO artifacts VALUES (2, 1, 999, 'orphan', 'text/plain', 'orphan')")
        self.db.commit()
        self.assertNotEqual(self.cli('create','--database',self.database,'--output',self.backup).returncode, 0)
        self.assertFalse(self.backup.exists())

if __name__ == '__main__': unittest.main()
