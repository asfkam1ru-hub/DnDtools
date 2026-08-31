"""Tests for Stage 4 Step 4.2 — base Character domain contract."""

from __future__ import annotations

import ast
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.domain.generic_character import GenericCharacter
from app.domain.lifecycle import CharacterLifecycleState

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = ROOT / "backend" / "app" / "domain"

OWNER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")

FORBIDDEN_RPG_FIELD_NAMES = frozenset(
    {
        "race",
        "species",
        "ancestry",
        "class",
        "class_name",
        "occupation",
        "level",
        "hp",
        "max_hp",
        "ac",
        "armor_class",
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
        "skills",
        "spells",
        "abilities",
        "inventory",
        "sanity",
        "luck",
        "cyberware",
        "system_resources",
        "game_system_id",
        "campaign_id",
        "profiles",
    }
)

FORBIDDEN_IMPORT_PREFIXES = (
    "app.persistence",
    "app.tools",
    "app.providers",
    "app.services",
    "app.main",
    "app.game_systems",
    "fastapi",
    "sqlalchemy",
    "openai",
)


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class BaseCharacterContractTests(unittest.TestCase):
    """Step 4.2 — system-independent base Character domain contract."""

    def test_valid_minimal_character_with_required_fields(self):
        character = GenericCharacter(name="Aria", owner_id=OWNER_ID)
        self.assertEqual(character.name, "Aria")
        self.assertEqual(character.owner_id, OWNER_ID)
        self.assertEqual(character.description, "")
        self.assertEqual(character.lifecycle_state, CharacterLifecycleState.ACTIVE)
        self.assertIsInstance(character.id, uuid.UUID)

    def test_character_valid_with_zero_profiles(self):
        """Zero profiles — no profiles field on base Character."""
        character = GenericCharacter(name="Library-only", owner_id=OWNER_ID)
        self.assertEqual(character.name, "Library-only")
        self.assertFalse(hasattr(character, "profiles"))

    def test_owner_id_is_required(self):
        with self.assertRaises(ValidationError):
            GenericCharacter(name="Aria")

    def test_owner_id_must_be_uuid(self):
        with self.assertRaises(ValidationError):
            GenericCharacter(name="Aria", owner_id="not-a-uuid")

    def test_generated_id_is_uuid(self):
        character = GenericCharacter(name="Aria", owner_id=OWNER_ID)
        self.assertIsInstance(character.id, uuid.UUID)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValidationError):
            GenericCharacter(name="", owner_id=OWNER_ID)

    def test_whitespace_only_name_rejected(self):
        with self.assertRaises(ValidationError):
            GenericCharacter(name="   ", owner_id=OWNER_ID)

    def test_lifecycle_defaults_to_active(self):
        character = GenericCharacter(name="Aria", owner_id=OWNER_ID)
        self.assertEqual(character.lifecycle_state, CharacterLifecycleState.ACTIVE)

    def test_archived_lifecycle_state_is_valid(self):
        character = GenericCharacter(
            name="Aria",
            owner_id=OWNER_ID,
            lifecycle_state=CharacterLifecycleState.ARCHIVED,
        )
        self.assertEqual(character.lifecycle_state, CharacterLifecycleState.ARCHIVED)

    def test_created_at_is_timezone_aware(self):
        character = GenericCharacter(name="Aria", owner_id=OWNER_ID)
        self.assertIsNotNone(character.created_at.tzinfo)

    def test_updated_at_is_timezone_aware(self):
        character = GenericCharacter(name="Aria", owner_id=OWNER_ID)
        self.assertIsNotNone(character.updated_at.tzinfo)

    def test_json_serialization_succeeds(self):
        fixed_id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
        character = GenericCharacter(
            id=fixed_id,
            owner_id=OWNER_ID,
            name="Aria",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        payload = character.model_dump(mode="json")
        self.assertEqual(payload["id"], str(fixed_id))
        self.assertEqual(payload["owner_id"], str(OWNER_ID))
        self.assertEqual(payload["lifecycle_state"], "active")

    def test_base_character_has_no_rpg_mechanic_fields(self):
        field_names = set(GenericCharacter.model_fields)
        overlap = field_names & FORBIDDEN_RPG_FIELD_NAMES
        self.assertEqual(
            overlap,
            set(),
            f"base Character must not expose RPG fields: {sorted(overlap)}",
        )

    def test_base_domain_modules_have_no_forbidden_imports(self):
        base_modules = (
            DOMAIN_DIR / "__init__.py",
            DOMAIN_DIR / "generic_character.py",
            DOMAIN_DIR / "lifecycle.py",
        )
        for path in base_modules:
            with self.subTest(module=path.name):
                imported = _imported_modules(path)
                for module in imported:
                    for prefix in FORBIDDEN_IMPORT_PREFIXES:
                        self.assertFalse(
                            module.startswith(prefix),
                            f"{path.name} must not import {module}",
                        )

    def test_domain_init_exports_only_base_character_contracts(self):
        import app.domain as domain_pkg

        self.assertEqual(
            set(domain_pkg.__all__),
            {"CharacterLifecycleState", "GenericCharacter"},
        )


if __name__ == "__main__":
    unittest.main()
