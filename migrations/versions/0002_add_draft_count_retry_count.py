"""Add draft_count and retry_count to generation_runs

Revision ID: 0002_add_draft_count_retry_count
Revises: 0001_initial_schema
Create Date: 2026-10-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_draft_count_retry_count"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default is required for NOT NULL columns added to a table that may
    # already contain rows — SQLite cannot back-fill a plain default otherwise.
    op.add_column(
        "generation_runs",
        sa.Column(
            "draft_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "generation_runs",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("generation_runs", "retry_count")
    op.drop_column("generation_runs", "draft_count")
