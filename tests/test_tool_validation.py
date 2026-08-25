import unittest
from copy import deepcopy
from unittest.mock import MagicMock

from app.tools.character import (
    CREATE_CHARACTER_TOOL,
    GET_CHARACTER_TOOL,
    LIST_CHARACTERS_TOOL,
    UPDATE_CHARACTER_TOOL,
    character_tool_bindings,
)
from app.tools.registry import ToolBinding, ToolRegistry
from app.tools.schema import ToolDefinition
from app.tools.validation import (
    ToolArgumentsValidationError,
    ToolValidationError,
    ToolValidator,
)


VALID_CREATE_ARGS = {
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


def make_definition(
    name: str,
    parameters: dict,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"{name} tool",
        parameters=parameters,
    )


class ToolValidationTests(unittest.TestCase):
    def setUp(self):
        self.handler = MagicMock()
        self.registry = ToolRegistry()
        self.registry.register(
            ToolBinding(
                make_definition(
                    "demo_tool",
                    {
                        "type": "object",
                        "properties": {
                            "character_id": {"type": "string", "minLength": 1},
                            "level": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 20,
                            },
                            "active": {"type": "boolean"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "profile": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                },
                                "required": ["title"],
                                "additionalProperties": False,
                            },
                            "score": {
                                "type": "integer",
                                "exclusiveMinimum": 0,
                            },
                        },
                        "required": ["character_id"],
                        "additionalProperties": False,
                    },
                ),
                self.handler,
            )
        )
        self.validator = ToolValidator(self.registry)

    def test_registered_tool_with_valid_args_accepted(self):
        result = self.validator.validate(
            "demo_tool",
            {"character_id": "abc"},
        )
        self.assertEqual(result, {"character_id": "abc"})

    def test_result_is_dict(self):
        result = self.validator.validate("demo_tool", {"character_id": "abc"})
        self.assertIsInstance(result, dict)

    def test_original_arguments_not_mutated(self):
        arguments = {"character_id": "abc", "tags": ["one"]}
        snapshot = deepcopy(arguments)
        self.validator.validate("demo_tool", arguments)
        self.assertEqual(arguments, snapshot)

    def test_unknown_tool_rejected(self):
        with self.assertRaises(ToolValidationError):
            self.validator.validate("missing_tool", {})

    def test_arguments_none_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate("demo_tool", None)

    def test_arguments_non_object_rejected(self):
        for bad in (["x"], "x", 1, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ToolArgumentsValidationError):
                    self.validator.validate("demo_tool", bad)

    def test_missing_required_field_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError) as ctx:
            self.validator.validate("demo_tool", {})
        self.assertIn("character_id", str(ctx.exception))

    def test_unknown_arg_rejected_when_additional_properties_false(self):
        with self.assertRaises(ToolArgumentsValidationError) as ctx:
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "dangerous_extra": "nope"},
            )
        self.assertIn("dangerous_extra", str(ctx.exception))

    def test_allowed_properties_accepted(self):
        result = self.validator.validate(
            "demo_tool",
            {
                "character_id": "abc",
                "level": 5,
                "active": True,
                "tags": ["stealth"],
            },
        )
        self.assertEqual(result["level"], 5)
        self.assertEqual(result["active"], True)
        self.assertEqual(result["tags"], ["stealth"])

    def test_valid_string_accepted(self):
        result = self.validator.validate("demo_tool", {"character_id": "ok"})
        self.assertEqual(result["character_id"], "ok")

    def test_wrong_string_type_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate("demo_tool", {"character_id": 123})

    def test_min_length_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate("demo_tool", {"character_id": ""})

    def test_valid_integer_accepted(self):
        result = self.validator.validate(
            "demo_tool",
            {"character_id": "abc", "level": 3},
        )
        self.assertEqual(result["level"], 3)

    def test_string_integer_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "level": "12"},
            )

    def test_bool_rejected_as_integer(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "level": True},
            )

    def test_minimum_enforced(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "level": 0},
            )

    def test_maximum_enforced(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "level": 21},
            )

    def test_exclusive_minimum_enforced(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "score": 0},
            )
        result = self.validator.validate(
            "demo_tool",
            {"character_id": "abc", "score": 1},
        )
        self.assertEqual(result["score"], 1)

    def test_valid_bool_accepted(self):
        result = self.validator.validate(
            "demo_tool",
            {"character_id": "abc", "active": False},
        )
        self.assertIs(result["active"], False)

    def test_int_rejected_as_bool(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "active": 1},
            )

    def test_valid_list_accepted(self):
        result = self.validator.validate(
            "demo_tool",
            {"character_id": "abc", "tags": ["a", "b"]},
        )
        self.assertEqual(result["tags"], ["a", "b"])

    def test_non_list_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "tags": "stealth"},
            )

    def test_invalid_item_type_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {"character_id": "abc", "tags": ["ok", 1]},
            )

    def test_nested_object_validation(self):
        result = self.validator.validate(
            "demo_tool",
            {
                "character_id": "abc",
                "profile": {"title": "Ranger"},
            },
        )
        self.assertEqual(result["profile"], {"title": "Ranger"})

        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "demo_tool",
                {
                    "character_id": "abc",
                    "profile": {"title": "Ranger", "extra": "nope"},
                },
            )

    def test_validated_result_does_not_share_mutable_nested_refs(self):
        arguments = {"character_id": "abc", "tags": ["one"]}
        result = self.validator.validate("demo_tool", arguments)
        result["tags"].append("two")
        self.assertEqual(arguments["tags"], ["one"])


class CharacterToolValidationTests(unittest.TestCase):
    def setUp(self):
        self.tools = MagicMock()
        self.registry = ToolRegistry()
        for binding in character_tool_bindings(self.tools):
            self.registry.register(binding)
        self.validator = ToolValidator(self.registry)

    def test_valid_get_character_args_accepted(self):
        result = self.validator.validate(
            "get_character",
            {"character_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        self.assertEqual(
            result,
            {"character_id": "123e4567-e89b-12d3-a456-426614174000"},
        )

    def test_get_character_extra_arg_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "get_character",
                {
                    "character_id": "123e4567-e89b-12d3-a456-426614174000",
                    "dangerous_extra": "nope",
                },
            )

    def test_list_characters_accepts_empty_object(self):
        self.assertEqual(self.validator.validate("list_characters", {}), {})

    def test_list_characters_rejects_extra_arg(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate("list_characters", {"extra": 1})

    def test_valid_create_character_arguments_accepted(self):
        result = self.validator.validate("create_character", VALID_CREATE_ARGS)
        self.assertEqual(result["name"], "Aria")
        self.assertEqual(result["level"], 1)

    def test_create_missing_required_rejected(self):
        payload = dict(VALID_CREATE_ARGS)
        del payload["name"]
        with self.assertRaises(ToolArgumentsValidationError) as ctx:
            self.validator.validate("create_character", payload)
        self.assertIn("name", str(ctx.exception))

    def test_create_level_above_20_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "create_character",
                {**VALID_CREATE_ARGS, "level": 21},
            )

    def test_create_ability_above_30_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "create_character",
                {**VALID_CREATE_ARGS, "strength": 31},
            )

    def test_create_inventory_item_non_string_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError):
            self.validator.validate(
                "create_character",
                {**VALID_CREATE_ARGS, "inventory": ["Sword", 1]},
            )

    def test_valid_partial_update_accepted(self):
        result = self.validator.validate(
            "update_character",
            {
                "character_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Aria Updated",
            },
        )
        self.assertEqual(result["name"], "Aria Updated")

    def test_update_without_character_id_rejected(self):
        with self.assertRaises(ToolArgumentsValidationError) as ctx:
            self.validator.validate("update_character", {"name": "Aria"})
        self.assertIn("character_id", str(ctx.exception))

    def test_handler_not_called_during_validation(self):
        self.validator.validate(
            "get_character",
            {"character_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        self.tools.get_character.assert_not_called()
        self.tools.create_character.assert_not_called()

    def test_validator_has_no_public_execution_methods(self):
        public_names = {
            name for name in dir(ToolValidator) if not name.startswith("_")
        }
        self.assertTrue(
            {"execute", "dispatch", "invoke", "run"}.isdisjoint(public_names)
        )

    def test_definitions_remain_provider_neutral(self):
        for tool in (
            GET_CHARACTER_TOOL,
            LIST_CHARACTERS_TOOL,
            CREATE_CHARACTER_TOOL,
            UPDATE_CHARACTER_TOOL,
        ):
            dumped = tool.model_dump()
            self.assertEqual(
                set(dumped.keys()),
                {"name", "description", "parameters"},
            )
            self.assertNotIn("function", dumped)


if __name__ == "__main__":
    unittest.main()
