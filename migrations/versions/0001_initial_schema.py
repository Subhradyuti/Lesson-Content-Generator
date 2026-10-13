"""Initial schema — all tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── generation_runs ───────────────────────────────────────────────────────
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("learner_profile", sa.Text, nullable=False),
        sa.Column("language", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("max_retries", sa.Integer, nullable=False),
        sa.Column("attempt_count", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("rubric_version", sa.String(100), nullable=False),
        sa.Column("model_provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("error_detail", sa.Text, nullable=True),
    )
    op.create_index("ix_generation_runs_status", "generation_runs", ["status"])
    op.create_index("ix_generation_runs_created_at", "generation_runs", ["created_at"])

    # ── lesson_drafts ─────────────────────────────────────────────────────────
    op.create_table(
        "lesson_drafts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("lesson_content", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
    )
    op.create_index("ix_lesson_drafts_run_id", "lesson_drafts", ["run_id"])

    # ── evaluations ───────────────────────────────────────────────────────────
    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "draft_id",
            sa.String(36),
            sa.ForeignKey("lesson_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rubric_version", sa.String(100), nullable=False),
        sa.Column("overall_pass", sa.Boolean, nullable=False),
        sa.Column("evaluation_json", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluator_model", sa.String(200), nullable=False),
    )
    op.create_index("ix_evaluations_draft_id", "evaluations", ["draft_id"])

    # ── revision_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "revision_logs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("failed_checkpoint_ids", JSON, nullable=False),
        sa.Column("revision_instructions", JSON, nullable=False),
        sa.Column("failed_checks_detail", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_error", sa.Text, nullable=True),
    )
    op.create_index("ix_revision_logs_run_id", "revision_logs", ["run_id"])

    # ── improvement_candidates ────────────────────────────────────────────────
    op.create_table(
        "improvement_candidates",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("candidate_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence_summary", sa.Text, nullable=True),
        sa.Column("benchmark_results", JSON, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", JSON, nullable=True),
    )
    op.create_index("ix_improvement_candidates_status", "improvement_candidates", ["status"])

    # ── configuration_versions ────────────────────────────────────────────────
    op.create_table(
        "configuration_versions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("config_type", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.UniqueConstraint("config_type", "version", name="uq_config_type_version"),
    )
    op.create_index(
        "ix_configuration_versions_config_type",
        "configuration_versions",
        ["config_type"],
    )
    op.create_index(
        "ix_configuration_versions_active",
        "configuration_versions",
        ["active"],
    )


def downgrade() -> None:
    op.drop_table("configuration_versions")
    op.drop_table("improvement_candidates")
    op.drop_table("revision_logs")
    op.drop_table("evaluations")
    op.drop_table("lesson_drafts")
    op.drop_table("generation_runs")
