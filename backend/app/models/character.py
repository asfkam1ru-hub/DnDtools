"""
Character model — Stage 2, Step 1.

WHY Pydantic and not a plain dataclass?
- FastAPI already depends on Pydantic, so no new package is needed.
- Pydantic runs validation automatically when you call Character(...).
  If any field breaks a rule, it raises a clear ValidationError immediately.
- This same class will later become the FastAPI request/response schema,
  keeping the model and the API contract in one place.

WHY no database yet?
- We define *what* a character looks like before deciding *where* to store it.
  That separation makes it easy to swap storage (SQLite, Postgres, etc.)
  later without rewriting validation rules.
"""

import uuid
from pydantic import BaseModel, Field, model_validator


class Character(BaseModel):
    # --- Identity ---
    # uuid4 generates a random, globally-unique ID every time.
    # default_factory means Python calls uuid.uuid4() fresh for each instance.
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    name: str = Field(..., min_length=1)   # ... means "required"
    race: str = Field(..., min_length=1)
    class_name: str = Field(..., min_length=1)

    # --- Progression ---
    # D&D characters go from level 1 to 20. ge/le = greater/less than or equal.
    level: int = Field(..., ge=1, le=20)

    # --- Hit Points ---
    max_hp: int = Field(..., gt=0)          # must be positive
    hp: int = Field(..., ge=0)              # can be 0 (unconscious), never negative
    inventory: list[str] = Field(default_factory=list)

    # --- Ability Scores ---
    # D&D ability scores range 1–30 (20 is typical human max; 30 is theoretical cap).
    strength: int = Field(..., ge=1, le=30)
    dexterity: int = Field(..., ge=1, le=30)
    constitution: int = Field(..., ge=1, le=30)
    intelligence: int = Field(..., ge=1, le=30)
    wisdom: int = Field(..., ge=1, le=30)
    charisma: int = Field(..., ge=1, le=30)

    @model_validator(mode="after")
    def hp_cannot_exceed_max_hp(self) -> "Character":
        """
        WHY a cross-field validator?
        Individual Field constraints only check one field in isolation.
        hp ≤ max_hp is a *relationship* between two fields, so we need
        a model-level validator that runs after all fields are set.
        """
        if self.hp > self.max_hp:
            raise ValueError(
                f"hp ({self.hp}) cannot exceed max_hp ({self.max_hp})"
            )
        return self
