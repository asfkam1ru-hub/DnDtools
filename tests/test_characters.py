import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.main import (
    app,
    character_repository,
    create_character,
    delete_character,
    get_character,
    list_characters,
    update_character,
)
from app.models.character import Character
from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.schemas.character import CharacterCreate, CharacterUpdate


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


class CharacterCRUDTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self._db_path = Path(self._tmp_dir.name) / "test_characters.db"
        self._db_url = f"sqlite:///{self._db_path}"

        self._engine = create_engine_for_url(self._db_url)
        self._session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)

        self._previous_repository = character_repository

        # Swap repository used by app endpoints to isolate tests from production DB.
        import app.main as main_module

        main_module.character_repository = CharacterRepository(self._session_factory)
        self._main_module = main_module

    def tearDown(self):
        self._main_module.character_repository = self._previous_repository
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_post_creates_character_and_returns_201(self):
        payload = CharacterCreate(**VALID_CHARACTER_DATA)
        created = create_character(payload)

        self.assertIsNotNone(created.id)
        self.assertEqual(created.name, VALID_CHARACTER_DATA["name"])
        self.assertEqual(created.inventory, [])
        self.assertEqual(created.skills, [])

    def test_created_character_appears_in_get_characters(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))

        items = list_characters()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, created.id)

    def test_get_character_by_id_returns_existing_character(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))
        fetched = get_character(created.id)

        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.name, created.name)

    def test_get_character_by_id_returns_404_for_unknown_uuid(self):
        missing_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        with self.assertRaises(HTTPException) as ctx:
            get_character(missing_id)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_only_provided_fields(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))
        patch_data = CharacterUpdate(name="Aria Updated")
        patched = update_character(created.id, patch_data)

        self.assertEqual(patched.name, "Aria Updated")
        self.assertEqual(patched.race, VALID_CHARACTER_DATA["race"])
        self.assertEqual(patched.max_hp, VALID_CHARACTER_DATA["max_hp"])

    def test_patch_returns_404_for_unknown_uuid(self):
        missing_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        with self.assertRaises(HTTPException) as ctx:
            update_character(missing_id, CharacterUpdate(hp=5))
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_rejects_hp_greater_than_max_hp(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))

        # Patching hp alone must not break hp <= max_hp invariant.
        with self.assertRaises(ValidationError):
            update_character(created.id, CharacterUpdate(hp=99))

    def test_delete_removes_character_and_returns_204(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))

        delete_response = delete_character(created.id)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(HTTPException) as ctx:
            get_character(created.id)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_returns_404_for_unknown_uuid(self):
        missing_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        with self.assertRaises(HTTPException) as ctx:
            delete_character(missing_id)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_record_persists_across_new_session_factory(self):
        created = create_character(CharacterCreate(**VALID_CHARACTER_DATA))

        # Simulate app restart/session recreation by building a fresh repository
        # against the same SQLite file.
        import app.main as main_module

        reopened_engine = create_engine_for_url(self._db_url)
        reopened_factory = create_session_factory(reopened_engine)
        main_module.character_repository = CharacterRepository(reopened_factory)
        try:
            fetched = get_character(created.id)
        finally:
            # Restore repository for remaining tests in this case.
            main_module.character_repository = CharacterRepository(self._session_factory)
            reopened_engine.dispose()

        self.assertEqual(fetched.id, created.id)

    def test_character_rejects_hp_above_max_hp(self):
        invalid_data = {**VALID_CHARACTER_DATA, "hp": 13}

        with self.assertRaisesRegex(ValidationError, "cannot exceed max_hp"):
            Character(**invalid_data)

    def test_post_route_is_registered(self):
        route = next(route for route in app.routes if route.path == "/characters")
        self.assertIn("POST", route.methods)


if __name__ == "__main__":
    unittest.main()
