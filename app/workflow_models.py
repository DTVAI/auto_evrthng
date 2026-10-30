from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db import Base
from .models import now


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("kind", "source_ref"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    source_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    payload: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    generation: Mapped[int] = mapped_column(Integer)
    tool_id: Mapped[str] = mapped_column(String(80))
    dependencies: Mapped[str] = mapped_column(Text)
    input: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    case_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(80))
    step_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CaseClaim(Base):
    __tablename__ = "case_claims"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), primary_key=True)
    identity: Mapped[str] = mapped_column(String(200))
    deputy_for: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
