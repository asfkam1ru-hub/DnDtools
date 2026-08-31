"""Platform-neutral base Character domain contracts (Stage 4, Step 4.2)."""

from app.domain.generic_character import GenericCharacter
from app.domain.lifecycle import CharacterLifecycleState

__all__ = [
    "CharacterLifecycleState",
    "GenericCharacter",
]
