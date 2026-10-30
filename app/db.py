import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("TOOLBOX_DATABASE_URL", "sqlite:///./toolbox.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(engine)

def get_db():
    with SessionLocal() as db:
        yield db
