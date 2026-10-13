"""
SQLAlchemy models for persistent storage.
All run data is stored with relationships to enable full audit trails.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class GenerationRun(Base):
    """Top-level record for each lesson generation request."""

    __tablename__ = "generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    learner_profile: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(100), nullable=False, default="simple English")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draft_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    drafts: Mapped[list[LessonDraft]] = relationship(
        "LessonDraft", back_populates="run", cascade="all, delete-orphan"
    )
    revision_logs: Mapped[list[RevisionLog]] = relationship(
        "RevisionLog", back_populates="run", cascade="all, delete-orphan"
    )


class LessonDraft(Base):
    """Each draft produced during a generation run."""

    __tablename__ = "lesson_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_runs.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    run: Mapped[GenerationRun] = relationship("GenerationRun", back_populates="drafts")
    evaluations: Mapped[list[Evaluation]] = relationship(
        "Evaluation", back_populates="draft", cascade="all, delete-orphan"
    )

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class Evaluation(Base):
    """Evaluation result for a specific draft."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    draft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("lesson_drafts.id"), nullable=False
    )
    rubric_version: Mapped[str] = mapped_column(String(100), nullable=False)
    overall_pass: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evaluation_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    evaluator_model: Mapped[str] = mapped_column(String(200), nullable=False)

    # Relationships
    draft: Mapped[LessonDraft] = relationship("LessonDraft", back_populates="evaluations")


class RevisionLog(Base):
    """Log of each revision attempt — which checks failed and what instructions were given."""

    __tablename__ = "revision_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_runs.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_checkpoint_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    revision_instructions: Mapped[list] = mapped_column(JSON, nullable=False)
    failed_checks_detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    evaluation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped[GenerationRun] = relationship("GenerationRun", back_populates="revision_logs")


class ImprovementCandidate(Base):
    """
    Versioned candidate for improving generator prompts, evaluator prompts, or rubrics.
    Candidates must go through: proposed → testing → approved/rejected → active or rolled_back.
    Human approval is required before a candidate can become active.
    """

    __tablename__ = "improvement_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    candidate_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # generator_prompt, rubric, etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    benchmark_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="proposed")
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # The proposed change content


class ConfigurationVersion(Base):
    """
    Version history for prompts, rubrics, and model configuration.
    Only one version can be active per config_type at a time.
    """

    __tablename__ = "configuration_versions"
    __table_args__ = (UniqueConstraint("config_type", "version", name="uq_config_type_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    config_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # generator_prompt, evaluator_prompt, rubric, model_config
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
