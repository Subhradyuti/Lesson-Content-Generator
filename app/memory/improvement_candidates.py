"""
Improvement candidate management.
Candidates must be approved by a human before becoming active.
The system never autonomously activates its own rubric or prompt changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import ImprovementCandidate
from app.db.session import get_db_session

logger = get_logger(__name__)

# Valid status transitions
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"testing", "rejected"},
    "testing": {"approved", "rejected"},
    "approved": {"active", "rolled_back"},
    "active": {"rolled_back"},
    "rejected": set(),
    "rolled_back": {"proposed"},  # Can re-propose
}


def create_candidate(
    candidate_type: str,
    description: str,
    evidence_summary: str | None = None,
    content: dict | None = None,
    created_by: str | None = None,
) -> str:
    """Create a new improvement candidate in 'proposed' state. Returns the candidate ID."""
    valid_types = {"generator_prompt", "evaluator_prompt", "rubric", "model_config"}
    if candidate_type not in valid_types:
        raise ValueError(f"Invalid candidate_type. Must be one of: {valid_types}")

    with get_db_session() as session:
        candidate = ImprovementCandidate(
            candidate_type=candidate_type,
            description=description,
            evidence_summary=evidence_summary,
            content=content or {},
            status="proposed",
            created_by=created_by,
        )
        session.add(candidate)
        session.flush()
        candidate_id = candidate.id

    logger.info(
        "Improvement candidate created",
        extra={"candidate_id": candidate_id, "type": candidate_type},
    )
    return candidate_id


def advance_candidate_status(
    candidate_id: str,
    new_status: str,
    approved_by: str | None = None,
    benchmark_results: dict | None = None,
) -> None:
    """
    Advance a candidate to the next status in its lifecycle.
    Raises ValueError if the transition is not allowed.
    Human approval (approved_by) is required when activating.
    """
    with get_db_session() as session:
        candidate = session.get(ImprovementCandidate, candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        current = candidate.status
        if new_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid transition: {current} → {new_status}. "
                f"Valid next states: {_VALID_TRANSITIONS.get(current, set())}"
            )

        # Human approval is mandatory for activation
        if new_status in ("approved", "active") and not approved_by:
            raise ValueError(
                f"approved_by is required to transition to '{new_status}'. "
                "Human approval is mandatory for this operation."
            )

        candidate.status = new_status
        if approved_by:
            candidate.approved_by = approved_by
            candidate.approved_at = datetime.now(UTC)
        if benchmark_results:
            candidate.benchmark_results = benchmark_results

    logger.info(
        "Candidate status advanced",
        extra={
            "candidate_id": candidate_id,
            "from_status": current,
            "to_status": new_status,
            "approved_by": approved_by,
        },
    )


def get_candidate(candidate_id: str) -> dict[str, Any] | None:
    """Retrieve a candidate by ID."""
    with get_db_session() as session:
        candidate = session.get(ImprovementCandidate, candidate_id)
        if candidate is None:
            return None
        return {
            "id": candidate.id,
            "candidate_type": candidate.candidate_type,
            "description": candidate.description,
            "evidence_summary": candidate.evidence_summary,
            "benchmark_results": candidate.benchmark_results,
            "status": candidate.status,
            "created_by": candidate.created_by,
            "approved_by": candidate.approved_by,
            "created_at": candidate.created_at.isoformat(),
            "approved_at": candidate.approved_at.isoformat() if candidate.approved_at else None,
            "content": candidate.content,
        }


def list_candidates(status: str | None = None) -> list[dict[str, Any]]:
    """List all candidates, optionally filtered by status."""
    with get_db_session() as session:
        stmt = select(ImprovementCandidate).order_by(ImprovementCandidate.created_at.desc())
        if status:
            stmt = stmt.where(ImprovementCandidate.status == status)
        candidates = list(session.scalars(stmt))
        return [
            {
                "id": c.id,
                "candidate_type": c.candidate_type,
                "description": c.description,
                "status": c.status,
                "created_by": c.created_by,
                "approved_by": c.approved_by,
                "created_at": c.created_at.isoformat(),
            }
            for c in candidates
        ]
