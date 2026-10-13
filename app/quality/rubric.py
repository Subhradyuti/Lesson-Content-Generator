"""
Rubric loading and schema definitions.
The rubric file (YAML) is the authoritative definition of what checkpoints are required.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# Path to the rubric directory relative to this file's location
_RUBRIC_DIR = Path(__file__).parent.parent.parent / "rubric"


class CheckpointDefinition(BaseModel):
    id: str
    dimension: str
    pass_condition: str
    mandatory: bool = True


class RubricDefinition(BaseModel):
    version: str
    description: str
    checkpoints: list[CheckpointDefinition]

    @property
    def mandatory_ids(self) -> frozenset[str]:
        return frozenset(c.id for c in self.checkpoints if c.mandatory)

    @property
    def all_ids(self) -> frozenset[str]:
        return frozenset(c.id for c in self.checkpoints)


@lru_cache(maxsize=8)
def load_rubric(version: str) -> RubricDefinition:
    """Load and validate a rubric from its YAML file."""
    rubric_path = _RUBRIC_DIR / f"{version}.yaml"
    if not rubric_path.exists():
        raise FileNotFoundError(f"Rubric file not found: {rubric_path}")

    with rubric_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    return RubricDefinition.model_validate(raw)


def get_mandatory_checkpoint_ids(version: str) -> frozenset[str]:
    """Return the set of mandatory checkpoint IDs for a rubric version."""
    return load_rubric(version).mandatory_ids
