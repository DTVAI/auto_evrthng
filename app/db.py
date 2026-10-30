import os
import stat
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("TOOLBOX_DATABASE_URL", "sqlite:///./toolbox.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _secure_sqlite_file():
    url = make_url(DATABASE_URL)
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
    ):
        return
    path = Path(url.database)
    # SQLite creates its journals and WAL files using the database's permissions.
    # Refuse existing insecure files rather than altering a user's data silently.
    if os.name == "posix":
        parent = path.parent.stat()
        if parent.st_mode & 0o022:
            raise PermissionError(
                f"SQLite parent directory must not be writable by other users: {path.parent}"
            )
        try:
            fd = os.open(
                path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
        except FileExistsError:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise PermissionError(
                    f"SQLite database must be a private regular file (0600): {path}"
                )
        else:
            os.close(fd)
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                info = sidecar.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                    raise PermissionError(f"SQLite sidecar must be private: {sidecar}")


if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_connect(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")


def init_db():
    from . import models, workflow_models  # noqa: F401

    if engine.dialect.name == "sqlite":
        _secure_sqlite_file()
        from .migrations import migrate

        migrate(engine)
    else:
        Base.metadata.create_all(engine)


def get_db():
    with SessionLocal() as db:
        yield db
