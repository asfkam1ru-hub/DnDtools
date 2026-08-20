import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app, character_repository
from app.models.character import Character
from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository


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


def assert_error_contract(test_case, payload, *, code: str, message: str):
    test_case.assertIn("error", payload)
    error = payload["error"]
    test_case.assertEqual(error["code"], code)
    test_case.assertEqual(error["message"], message)
    test_case.assertIn("details", error)


class CharacterHTTPTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self._db_path = Path(self._tmp_dir.name) / "test_characters.db"
        self._db_url = f"sqlite:///{self._db_path}"

        self._engine = create_engine_for_url(self._db_url)
        self._session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)

        self._previous_repository = character_repository

        import app.main as main_module

        main_module.character_repository = CharacterRepository(self._session_factory)
        self._main_module = main_module
        self.client = TestClient(app)

    def tearDown(self):
        self._main_module.character_repository = self._previous_repository
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_post_creates_character_and_returns_201(self):
        response = self.client.post("/characters", json=VALID_CHARACTER_DATA)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertIn("id", body)
        self.assertEqual(body["name"], VALID_CHARACTER_DATA["name"])
        self.assertEqual(body["inventory"], [])
        self.assertEqual(body["skills"], [])

    def test_created_character_appears_in_get_characters(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        list_response = self.client.get("/characters")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        items = list_response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], created_id)

    def test_get_character_by_id_returns_existing_character(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        get_response = self.client.get(f"/characters/{created_id}")

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.json()["id"], created_id)

    def test_get_unknown_character_returns_404_error_contract(self):
        response = self.client.get(f"/characters/{MISSING_ID}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_error_contract(
            self,
            response.json(),
            code="character_not_found",
            message="Character not found",
        )
        self.assertIsNone(response.json()["error"]["details"])

    def test_patch_updates_only_provided_fields(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        patch_response = self.client.patch(
            f"/characters/{created_id}",
            json={"name": "Aria Updated"},
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        patched = patch_response.json()
        self.assertEqual(patched["name"], "Aria Updated")
        self.assertEqual(patched["race"], VALID_CHARACTER_DATA["race"])
        self.assertEqual(patched["max_hp"], VALID_CHARACTER_DATA["max_hp"])

    def test_patch_unknown_character_returns_404_error_contract(self):
        response = self.client.patch(f"/characters/{MISSING_ID}", json={"hp": 5})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_error_contract(
            self,
            response.json(),
            code="character_not_found",
            message="Character not found",
        )

    def test_patch_hp_greater_than_max_hp_returns_422_error_contract(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        response = self.client.patch(f"/characters/{created_id}", json={"hp": 99})

        self.assertEqual(response.status_code, 422)
        assert_error_contract(
            self,
            response.json(),
            code="validation_error",
            message="Request validation failed",
        )
        self.assertIsNotNone(response.json()["error"]["details"])

    def test_delete_removes_character_and_returns_204(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        delete_response = self.client.delete(f"/characters/{created_id}")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(delete_response.content, b"")

        get_response = self.client.get(f"/characters/{created_id}")
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_unknown_character_returns_404_error_contract(self):
        response = self.client.delete(f"/characters/{MISSING_ID}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        assert_error_contract(
            self,
            response.json(),
            code="character_not_found",
            message="Character not found",
        )

    def test_post_invalid_payload_returns_422_error_contract(self):
        invalid_payload = {**VALID_CHARACTER_DATA, "level": 99}
        response = self.client.post("/characters", json=invalid_payload)

        self.assertEqual(response.status_code, 422)
        assert_error_contract(
            self,
            response.json(),
            code="validation_error",
            message="Request validation failed",
        )
        self.assertIsNotNone(response.json()["error"]["details"])

    def test_invalid_uuid_path_returns_422_error_contract(self):
        response = self.client.get("/characters/not-a-uuid")

        self.assertEqual(response.status_code, 422)
        assert_error_contract(
            self,
            response.json(),
            code="validation_error",
            message="Request validation failed",
        )
        self.assertIsNotNone(response.json()["error"]["details"])

    def test_record_persists_across_new_session_factory(self):
        create_response = self.client.post("/characters", json=VALID_CHARACTER_DATA)
        created_id = create_response.json()["id"]

        reopened_engine = create_engine_for_url(self._db_url)
        reopened_factory = create_session_factory(reopened_engine)
        self._main_module.character_repository = CharacterRepository(reopened_factory)
        try:
            fetched = self.client.get(f"/characters/{created_id}")
        finally:
            self._main_module.character_repository = CharacterRepository(
                self._session_factory
            )
            reopened_engine.dispose()

        self.assertEqual(fetched.status_code, status.HTTP_200_OK)
        self.assertEqual(fetched.json()["id"], created_id)

    def test_character_rejects_hp_above_max_hp(self):
        invalid_data = {**VALID_CHARACTER_DATA, "hp": 13}

        with self.assertRaisesRegex(ValidationError, "cannot exceed max_hp"):
            Character(**invalid_data)

    def test_post_route_is_registered(self):
        route = next(route for route in app.routes if route.path == "/characters")
        self.assertIn("POST", route.methods)


if __name__ == "__main__":
    unittest.main()
