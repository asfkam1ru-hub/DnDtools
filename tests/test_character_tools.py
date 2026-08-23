import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from pydantic import ValidationError

from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.tools.character import (
    CHARACTER_TOOL_DEFINITIONS,
    CREATE_CHARACTER_TOOL,
    DELETE_CHARACTER_TOOL,
    GET_CHARACTER_TOOL,
    LIST_CHARACTERS_TOOL,
    UPDATE_CHARACTER_TOOL,
    CharacterToolInputError,
    CharacterToolNotFoundError,
    CharacterTools,
)
from app.tools.schema import ToolDefinition


VALID_CHARACTER_DATA = {
    "name": "Aria",
    "race": "Elf",
    "class_name": "Ranger",
    "level": 1,
    "max_hp": 12,
    "hp": 12,
    "strength": 10,
    "dexterity": 16,
    "constitution": 12,
    "intelligence": 11,
    "wisdom": 14,
    "charisma": 9,
}

MISSING_ID = "123e4567-e89b-12d3-a456-426614174000"
INVALID_ID = "not-a-uuid"


class CharacterToolsTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_character_tools.db"
        self._engine = create_engine_for_url(f"sqlite:///{db_path}")
        session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)
        self.repository = CharacterRepository(session_factory)
        self.tools = CharacterTools(self.repository)

    def tearDown(self):
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_get_existing_character_returns_json_compatible_dict(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        result = self.tools.get_character(created["id"])

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], created["id"])
        self.assertIsInstance(result["id"], str)
        self.assertEqual(result["name"], "Aria")

    def test_get_unknown_character_raises_not_found(self):
        with self.assertRaises(CharacterToolNotFoundError):
            self.tools.get_character(MISSING_ID)

    def test_get_invalid_uuid_raises_input_error(self):
        with self.assertRaises(CharacterToolInputError):
            self.tools.get_character(INVALID_ID)

    def test_list_empty_repository_returns_empty_list(self):
        self.assertEqual(self.tools.list_characters(), [])

    def test_list_returns_multiple_characters(self):
        first = self.tools.create_character(**VALID_CHARACTER_DATA)
        second = self.tools.create_character(
            **{**VALID_CHARACTER_DATA, "name": "Borin", "race": "Dwarf"}
        )

        listed = self.tools.list_characters()

        self.assertEqual(len(listed), 2)
        ids = {item["id"] for item in listed}
        self.assertEqual(ids, {first["id"], second["id"]})

    def test_create_character_persists_character(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        fetched = self.repository.get(UUID(created["id"]))

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Aria")

    def test_create_character_returns_generated_id_as_json_string(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)

        self.assertIn("id", created)
        self.assertIsInstance(created["id"], str)
        UUID(created["id"])  # must be a valid UUID string

    def test_create_invalid_character_data_rejected(self):
        with self.assertRaises(ValidationError):
            self.tools.create_character(**{**VALID_CHARACTER_DATA, "level": 99})

    def test_create_hp_greater_than_max_hp_rejected(self):
        with self.assertRaises(ValidationError):
            self.tools.create_character(**{**VALID_CHARACTER_DATA, "hp": 99})

    def test_create_inventory_and_skills_round_trip(self):
        created = self.tools.create_character(
            **VALID_CHARACTER_DATA,
            inventory=["Longsword", "Potion"],
            skills=["Stealth", "Arcana"],
        )
        fetched = self.tools.get_character(created["id"])

        self.assertEqual(fetched["inventory"], ["Longsword", "Potion"])
        self.assertEqual(fetched["skills"], ["Stealth", "Arcana"])

    def test_partial_update_changes_only_provided_field(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        updated = self.tools.update_character(created["id"], name="Aria Updated")

        self.assertEqual(updated["name"], "Aria Updated")
        self.assertEqual(updated["race"], VALID_CHARACTER_DATA["race"])
        self.assertEqual(updated["max_hp"], VALID_CHARACTER_DATA["max_hp"])

    def test_update_persists_changes(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        self.tools.update_character(created["id"], name="Persisted")

        fetched = self.tools.get_character(created["id"])
        self.assertEqual(fetched["name"], "Persisted")

    def test_update_lowering_max_hp_below_hp_rejected(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)

        with self.assertRaises(ValidationError):
            self.tools.update_character(created["id"], max_hp=5)

    def test_update_unknown_character_rejected(self):
        with self.assertRaises(CharacterToolNotFoundError):
            self.tools.update_character(MISSING_ID, name="Ghost")

    def test_update_invalid_uuid_rejected(self):
        with self.assertRaises(CharacterToolInputError):
            self.tools.update_character(INVALID_ID, name="Ghost")

    def test_delete_existing_character_succeeds(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        result = self.tools.delete_character(created["id"])

        self.assertEqual(
            result,
            {"deleted": True, "character_id": created["id"]},
        )

    def test_deleted_character_no_longer_exists(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        self.tools.delete_character(created["id"])

        with self.assertRaises(CharacterToolNotFoundError):
            self.tools.get_character(created["id"])

    def test_delete_unknown_character_rejected(self):
        with self.assertRaises(CharacterToolNotFoundError):
            self.tools.delete_character(MISSING_ID)

    def test_delete_invalid_uuid_rejected(self):
        with self.assertRaises(CharacterToolInputError):
            self.tools.delete_character(INVALID_ID)

    def test_character_tool_definitions_exist(self):
        self.assertEqual(len(CHARACTER_TOOL_DEFINITIONS), 5)
        for tool in CHARACTER_TOOL_DEFINITIONS:
            self.assertIsInstance(tool, ToolDefinition)

    def test_character_tool_names_are_correct(self):
        names = [tool.name for tool in CHARACTER_TOOL_DEFINITIONS]
        self.assertEqual(
            names,
            [
                "get_character",
                "list_characters",
                "create_character",
                "update_character",
                "delete_character",
            ],
        )

    def test_character_tool_parameters_are_valid_tool_definitions(self):
        # Re-validating through ToolDefinition ensures schema contract holds.
        for tool in CHARACTER_TOOL_DEFINITIONS:
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            )

    def test_create_tool_does_not_expose_id(self):
        properties = CREATE_CHARACTER_TOOL.parameters["properties"]
        self.assertNotIn("id", properties)

    def test_update_tool_requires_character_id_and_optional_fields(self):
        params = UPDATE_CHARACTER_TOOL.parameters
        self.assertEqual(params["required"], ["character_id"])
        self.assertIn("character_id", params["properties"])
        self.assertIn("name", params["properties"])
        self.assertNotIn("name", params["required"])

    def test_definitions_have_no_openai_wrapper(self):
        for tool in CHARACTER_TOOL_DEFINITIONS:
            dumped = tool.model_dump()
            self.assertEqual(
                set(dumped.keys()),
                {"name", "description", "parameters"},
            )
            self.assertNotIn("function", dumped)

    def test_empty_update_is_noop(self):
        created = self.tools.create_character(**VALID_CHARACTER_DATA)
        updated = self.tools.update_character(created["id"])
        self.assertEqual(updated, created)


if __name__ == "__main__":
    unittest.main()
