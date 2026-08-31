"""Character lifecycle states (system-independent)."""

from enum import Enum


class CharacterLifecycleState(str, Enum):
    """Public character lifecycle states."""

    ACTIVE = "active"
    ARCHIVED = "archived"
