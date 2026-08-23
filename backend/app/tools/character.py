"""
Character CRUD tools (Phase 3, Step 3.5).

Defines ToolDefinition contracts and Python handlers that call
CharacterRepository directly.
"""

from uuid import UUID

from app.models.character import Character
from app.persistence.repository import CharacterRepository
from app.tools.registry import ToolBinding
from app.tools.schema import ToolDefinition


class CharacterToolError(Exception):
    """Base error for Character tool handlers."""


class CharacterToolInputError(CharacterToolError):
    """Raised when tool arguments are invalid (e.g. bad UUID)."""


class CharacterToolNotFoundError(CharacterToolError):
    """Raised when a character_id does not exist in persistence."""


_ABILITY_SCORE_SCHEMA = {
    "type": "integer",
    "minimum": 1,
    "maximum": 30,
}

_CHARACTER_CREATE_PROPERTIES = {
    "name": {"type": "string", "minLength": 1},
    "race": {"type": "string", "minLength": 1},
    "class_name": {"type": "string", "minLength": 1},
    "level": {"type": "integer", "minimum": 1, "maximum": 20},
    "max_hp": {"type": "integer", "exclusiveMinimum": 0},
    "hp": {"type": "integer", "minimum": 0},
    "inventory": {
        "type": "array",
        "items": {"type": "string"},
    },
    "skills": {
        "type": "array",
        "items": {"type": "string"},
    },
    "strength": _ABILITY_SCORE_SCHEMA,
    "dexterity": _ABILITY_SCORE_SCHEMA,
    "constitution": _ABILITY_SCORE_SCHEMA,
    "intelligence": _ABILITY_SCORE_SCHEMA,
    "wisdom": _ABILITY_SCORE_SCHEMA,
    "charisma": _ABILITY_SCORE_SCHEMA,
}

_CHARACTER_UPDATE_PROPERTIES = {
    "character_id": {"type": "string"},
    **_CHARACTER_CREATE_PROPERTIES,
}


GET_CHARACTER_TOOL = ToolDefinition(
    name="get_character",
    description="Get a character by id",
    parameters={
        "type": "object",
        "properties": {
            "character_id": {"type": "string"},
        },
        "required": ["character_id"],
        "additionalProperties": False,
    },
)

LIST_CHARACTERS_TOOL = ToolDefinition(
    name="list_characters",
    description="List all characters",
    parameters={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
)

CREATE_CHARACTER_TOOL = ToolDefinition(
    name="create_character",
    description="Create a new character",
    parameters={
        "type": "object",
        "properties": _CHARACTER_CREATE_PROPERTIES,
        "required": [
            "name",
            "race",
            "class_name",
            "level",
            "max_hp",
            "hp",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ],
        "additionalProperties": False,
    },
)

UPDATE_CHARACTER_TOOL = ToolDefinition(
    name="update_character",
    description="Partially update an existing character",
    parameters={
        "type": "object",
        "properties": _CHARACTER_UPDATE_PROPERTIES,
        "required": ["character_id"],
        "additionalProperties": False,
    },
)

DELETE_CHARACTER_TOOL = ToolDefinition(
    name="delete_character",
    description="Delete a character by id",
    parameters={
        "type": "object",
        "properties": {
            "character_id": {"type": "string"},
        },
        "required": ["character_id"],
        "additionalProperties": False,
    },
)

CHARACTER_TOOL_DEFINITIONS = (
    GET_CHARACTER_TOOL,
    LIST_CHARACTERS_TOOL,
    CREATE_CHARACTER_TOOL,
    UPDATE_CHARACTER_TOOL,
    DELETE_CHARACTER_TOOL,
)


class CharacterTools:
    """Character CRUD handlers bound to a CharacterRepository instance."""

    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository

    def get_character(self, character_id: str) -> dict:
        character = self._repository.get(self._parse_character_id(character_id))
        if character is None:
            raise CharacterToolNotFoundError("Character not found")
        return character.model_dump(mode="json")

    def list_characters(self) -> list[dict]:
        return [
            character.model_dump(mode="json")
            for character in self._repository.list()
        ]

    def create_character(self, **fields) -> dict:
        payload = dict(fields)
        payload.pop("id", None)
        # Domain Character validates all field rules, including hp <= max_hp.
        character = Character(**payload)
        created = self._repository.create(character)
        return created.model_dump(mode="json")

    def update_character(self, character_id: str, **updates) -> dict:
        existing = self._repository.get(self._parse_character_id(character_id))
        if existing is None:
            raise CharacterToolNotFoundError("Character not found")

        patch = dict(updates)
        patch.pop("id", None)
        patch.pop("character_id", None)

        # Empty update is a no-op that still returns the current character.
        merged = existing.model_dump() | patch
        updated = Character(**merged)
        persisted = self._repository.update(updated)
        if persisted is None:
            raise CharacterToolNotFoundError("Character not found")
        return persisted.model_dump(mode="json")

    def delete_character(self, character_id: str) -> dict:
        parsed_id = self._parse_character_id(character_id)
        deleted = self._repository.delete(parsed_id)
        if not deleted:
            raise CharacterToolNotFoundError("Character not found")
        return {
            "deleted": True,
            "character_id": str(parsed_id),
        }

    @staticmethod
    def _parse_character_id(character_id: str) -> UUID:
        try:
            return UUID(str(character_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise CharacterToolInputError(
                "character_id must be a valid UUID string"
            ) from exc


def character_tool_bindings(tools: CharacterTools) -> tuple[ToolBinding, ...]:
    """
    Explicitly pair Character ToolDefinitions with CharacterTools handlers.

    Bindings are built without reflection so renames stay visible at edit time.
    """
    return (
        ToolBinding(GET_CHARACTER_TOOL, tools.get_character),
        ToolBinding(LIST_CHARACTERS_TOOL, tools.list_characters),
        ToolBinding(CREATE_CHARACTER_TOOL, tools.create_character),
        ToolBinding(UPDATE_CHARACTER_TOOL, tools.update_character),
        ToolBinding(DELETE_CHARACTER_TOOL, tools.delete_character),
    )


__all__ = [
    "CHARACTER_TOOL_DEFINITIONS",
    "CREATE_CHARACTER_TOOL",
    "CharacterToolError",
    "CharacterToolInputError",
    "CharacterToolNotFoundError",
    "CharacterTools",
    "DELETE_CHARACTER_TOOL",
    "GET_CHARACTER_TOOL",
    "LIST_CHARACTERS_TOOL",
    "UPDATE_CHARACTER_TOOL",
    "character_tool_bindings",
]
