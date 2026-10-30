"""Versioned, non-destructive SQLite migrations and schema inspection."""

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.sqlite import dialect

SCHEMA_VERSION = 2
APPLICATION_ID = 0x54425831  # TBX1


def required_columns(version):
    from .db import Base
    from . import models, workflow_models  # noqa: F401

    result = {
        table.name: {column.name for column in table.columns}
        for table in Base.metadata.sorted_tables
    }
    if version < 2:
        for name in ("workflows", "workflow_steps", "workflow_events", "case_claims"):
            result.pop(name, None)
    if version == 0:
        result["revisions"] -= {"title", "subject_id"}
        # This table was introduced after the original schema and can be recreated empty.
        result.pop("job_requests")
    return result


def _affinity(declaration):
    """SQLite's documented type-affinity rules."""
    name = declaration.upper()
    if "INT" in name:
        return "INTEGER"
    if any(part in name for part in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if not name or "BLOB" in name:
        return "BLOB"
    if any(part in name for part in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


def validate_schema(db, version):
    if version not in (0, 1, SCHEMA_VERSION):
        raise ValueError(f"Unsupported application schema version: {version}")
    from .db import Base

    required = required_columns(version)
    for name, columns in required.items():
        table = Base.metadata.tables[name]
        rows = db.execute(f'PRAGMA table_info("{name}")').fetchall()
        actual = {row[1]: row for row in rows}
        if not columns <= actual.keys():
            raise ValueError(
                f"Invalid application schema: missing table or columns in {name}"
            )
        for column in table.columns:
            if column.name not in columns:
                continue
            row = actual[column.name]
            expected_type = column.type.compile(dialect=dialect())
            if _affinity(row[2]) != _affinity(expected_type):
                raise ValueError(
                    f"Invalid application schema: incompatible column type in {name}"
                )
            if not column.nullable and not column.primary_key and not row[3]:
                raise ValueError(
                    f"Invalid application schema: nullable required column in {name}"
                )
        expected_pk = tuple(column.name for column in table.primary_key.columns)
        actual_pk = tuple(
            row[1]
            for row in sorted((row for row in rows if row[5]), key=lambda row: row[5])
        )
        if actual_pk != expected_pk:
            raise ValueError(
                f"Invalid application schema: primary key missing in {name}"
            )
        expected_fk = {
            (fk.parent.name, fk.column.table.name, fk.column.name)
            for fk in table.foreign_keys
            if fk.parent.name in columns
        }
        actual_fk = {
            (row[3], row[2], row[4])
            for row in db.execute(f'PRAGMA foreign_key_list("{name}")')
        }
        if not expected_fk <= actual_fk:
            raise ValueError(
                f"Invalid application schema: foreign key missing in {name}"
            )
        expected_unique = {
            tuple(col.name for col in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        expected_unique.update(
            tuple(col.name for col in index.columns)
            for index in table.indexes
            if index.unique
        )
        if version == 0 and name == "revisions":
            expected_unique.discard(("case_id", "revision"))
        actual_unique = set()
        for index in db.execute(f'PRAGMA index_list("{name}")'):
            # Partial unique indexes do not enforce uniqueness for all records.
            if index[2] and not index[4]:
                actual_unique.add(
                    tuple(
                        row[2]
                        for row in db.execute(
                            "SELECT * FROM pragma_index_info(?) ORDER BY seqno",
                            (index[1],),
                        )
                    )
                )
        if not expected_unique <= actual_unique:
            raise ValueError(
                f"Invalid application schema: unique constraint missing in {name}"
            )


def migrate(engine):
    from .db import Base
    from . import models, workflow_models  # noqa: F401

    raw = engine.raw_connection()
    try:
        db = raw.driver_connection
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        tables = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if app_id not in (0, APPLICATION_ID) or (version and app_id != APPLICATION_ID):
            raise ValueError("Database application identity does not match Toolbox")
        if version > SCHEMA_VERSION:
            raise ValueError(f"Unsupported application schema version: {version}")
        if tables:
            validate_schema(db, version)
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Existing database has foreign key violations")
            if version == 0:
                columns = {
                    row[1] for row in db.execute('PRAGMA table_info("revisions")')
                }
                for column in ("title", "subject_id"):
                    if column not in columns:
                        db.execute(f"ALTER TABLE revisions ADD COLUMN {column} VARCHAR")
                # Unknown historical metadata remains NULL, including the latest revision.
                db.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_case_revision ON revisions(case_id, revision)"
                )
        db.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    # Create missing tables for a new DB, including the legacy job_requests table.
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"PRAGMA application_id={APPLICATION_ID}")
        connection.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
    raw = engine.raw_connection()
    try:
        validate_schema(raw.driver_connection, SCHEMA_VERSION)
        if raw.driver_connection.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Existing database has foreign key violations")
    finally:
        raw.close()
