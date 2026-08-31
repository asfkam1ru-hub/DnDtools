"""System-independent base Character domain model (Stage 4, Step 4.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.lifecycle import CharacterLifecycleState


def _utc_now() -> datetime:
    return datetime.now(UTC)


class GenericCharacter(BaseModel):
    """
    System-independent Character identity and library metadata.

    Canonical domain boundary for base Character (Step 4.2). D&D and other
    RPG mechanics live in system-specific profile models (Step 4.3+).

    A Character is valid with zero profiles; lifecycle does not depend on
    profile existence.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID
    name: str = Field(..., min_length=1)
    description: str = Field(default="", max_length=2048)
    biography: str = Field(default="", max_length=8192)
    personality: str = Field(default="", max_length=4096)
    notes: str = Field(default="", max_length=8192)
    avatar: str | None = Field(default=None, max_length=2048)
    appearance: str | None = Field(default=None, max_length=4096)
    lifecycle_state: CharacterLifecycleState = CharacterLifecycleState.ACTIVE
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty or whitespace-only")
        return stripped
