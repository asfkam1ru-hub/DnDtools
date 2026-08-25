"""Tests for Safe Execution Pipeline (Phase 3, Step 3.8)."""

import inspect
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from uuid import UUID

from pydantic import create_model

from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.tools.character import CharacterTools, character_tool_bindings
from app.tools.errors import ToolHandlerError
from app.tools.execution import (
    ToolExecutionErrorData,
    ToolExecutionResult,
    ToolExecutor,
    ensure_json_compatible,
)
from app.tools.registry import ToolBinding, ToolRegistry
from app.tools.schema import ToolDefinition
from app.tools.validation import ToolValidator


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

MISSING_ID = "123e4567-e89b-12d3-a456-426614174000"
INVALID_ID = "not-a-uuid"


def make_definition(name: str, parameters: dict) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"{name} tool",
        parameters=parameters,
    )


class ToolExecutionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.handler = MagicMock(return_value={"ok": True})
        self.empty_handler = MagicMock(return_value={"ok": True})
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
                        },
                        "required": ["character_id"],
                        "additionalProperties": False,
                    },
                ),
                self.handler,
            )
        )
        self.registry.register(
            ToolBinding(
                make_definition(
                    "empty_args_tool",
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                self.empty_handler,
            )
        )
        self.validator = ToolValidator(self.registry)
        self.executor = ToolExecutor(self.registry, self.validator)

    def test_valid_registered_tool_executes(self):
        result = self.executor.execute(
            "demo_tool",
            {"character_id": "abc"},
        )
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_handler_receives_validated_arguments(self):
        self.executor.execute("demo_tool", {"character_id": "abc", "level": 3})
        self.handler.assert_called_once_with(character_id="abc", level=3)

    def test_handler_called_exactly_once_on_success(self):
        self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertEqual(self.handler.call_count, 1)

    def test_success_result_contains_tool_name(self):
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertEqual(result.tool_name, "demo_tool")

    def test_output_preserved(self):
        self.handler.return_value = {"value": 42, "nested": {"a": 1}}
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertEqual(result.output, {"value": 42, "nested": {"a": 1}})

    def test_empty_arguments_tool_works(self):
        result = self.executor.execute("empty_args_tool", {})
        self.assertTrue(result.success)
        self.empty_handler.assert_called_once_with()

    def test_invalid_arguments_handler_not_called(self):
        result = self.executor.execute("demo_tool", {"character_id": 123})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_validation_error")
        self.handler.assert_not_called()

    def test_missing_required_handler_not_called(self):
        result = self.executor.execute("demo_tool", {})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_validation_error")
        self.handler.assert_not_called()

    def test_additional_property_handler_not_called(self):
        result = self.executor.execute(
            "demo_tool",
            {"character_id": "abc", "extra": True},
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_validation_error")
        self.handler.assert_not_called()

    def test_unknown_tool_no_handler_call(self):
        result = self.executor.execute("missing_tool", {"character_id": "abc"})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_validation_error")
        self.handler.assert_not_called()

    def test_expected_tool_error_converted_to_failure(self):
        self.handler.side_effect = ToolHandlerError("safe failure")
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_handler_error")
        self.assertEqual(result.error.message, "safe failure")
        self.assertIsNone(result.output)

    def test_pydantic_validation_error_converted_to_failure(self):
        Model = create_model("DemoModel", level=(int, ...))

        def bad_handler(**_kwargs):
            return Model(level="not-an-int")

        self.registry.register(
            ToolBinding(
                make_definition(
                    "domain_tool",
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                bad_handler,
            )
        )
        executor = ToolExecutor(self.registry, ToolValidator(self.registry))
        result = executor.execute("domain_tool", {})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_domain_validation_error")
        self.assertIsInstance(result.error.message, str)
        self.assertTrue(result.error.message)

    def test_error_result_has_deterministic_code_and_message(self):
        self.handler.side_effect = ToolHandlerError(
            "deterministic",
            code="tool_handler_error",
        )
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertEqual(
            result.error,
            ToolExecutionErrorData(
                code="tool_handler_error",
                message="deterministic",
            ),
        )

    def test_expected_errors_do_not_propagate(self):
        self.handler.side_effect = ToolHandlerError("no raise")
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertIsInstance(result, ToolExecutionResult)
        self.assertFalse(result.success)

    def test_runtime_error_from_handler_propagates(self):
        self.handler.side_effect = RuntimeError("database invariant broken")
        with self.assertRaises(RuntimeError) as ctx:
            self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertEqual(str(ctx.exception), "database invariant broken")

    def test_unexpected_exception_not_silently_converted(self):
        self.handler.side_effect = ValueError("unexpected programming bug")
        with self.assertRaises(ValueError):
            self.executor.execute("demo_tool", {"character_id": "abc"})

    def test_dict_output_accepted(self):
        self.handler.return_value = {"a": 1}
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertTrue(result.success)
        self.assertEqual(result.output, {"a": 1})

    def test_list_output_accepted(self):
        self.handler.return_value = [1, "x", True]
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertTrue(result.success)
        self.assertEqual(result.output, [1, "x", True])

    def test_scalar_json_output_accepted(self):
        for value in (None, "ok", 7, 1.5, True, False):
            with self.subTest(value=value):
                self.handler.return_value = value
                result = self.executor.execute(
                    "demo_tool",
                    {"character_id": "abc"},
                )
                self.assertTrue(result.success)
                self.assertEqual(result.output, value)

    def test_nested_json_output_accepted(self):
        payload = {"items": [{"n": 1}, {"n": 2}], "meta": {"ok": True}}
        self.handler.return_value = payload
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertTrue(result.success)
        self.assertEqual(result.output, payload)

    def test_custom_object_output_rejected(self):
        self.handler.return_value = object()
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_result_validation_error")

    def test_dict_with_non_string_key_rejected(self):
        self.handler.return_value = {1: "bad"}
        result = self.executor.execute("demo_tool", {"character_id": "abc"})
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_result_validation_error")

    def test_raw_arguments_unchanged(self):
        raw = {"character_id": "abc", "level": 2}
        snapshot = deepcopy(raw)
        self.executor.execute("demo_tool", raw)
        self.assertEqual(raw, snapshot)

    def test_no_getattr_eval_reflection_in_execute_source(self):
        source = inspect.getsource(ToolExecutor.execute)
        for forbidden in ("getattr(", "eval(", "exec(", "globals(", "locals("):
            self.assertNotIn(forbidden, source)

    def test_only_registered_binding_handler_invoked(self):
        other = MagicMock(return_value={"other": True})
        self.registry.register(
            ToolBinding(
                make_definition(
                    "other_tool",
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                other,
            )
        )
        executor = ToolExecutor(self.registry, ToolValidator(self.registry))
        executor.execute("demo_tool", {"character_id": "abc"})
        self.handler.assert_called_once()
        other.assert_not_called()


class EnsureJsonCompatibleHelperTests(unittest.TestCase):
    def test_helper_accepts_primitives_and_containers(self):
        self.assertEqual(ensure_json_compatible(None), None)
        self.assertEqual(ensure_json_compatible("x"), "x")
        self.assertEqual(ensure_json_compatible({"a": [1, True]}), {"a": [1, True]})

    def test_helper_rejects_custom_object(self):
        with self.assertRaises(Exception):
            ensure_json_compatible(object())


class CharacterToolExecutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_tool_execution.db"
        self._engine = create_engine_for_url(f"sqlite:///{db_path}")
        session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)
        self.repository = CharacterRepository(session_factory)
        self.tools = CharacterTools(self.repository)
        self.registry = ToolRegistry()
        for binding in character_tool_bindings(self.tools):
            self.registry.register(binding)
        self.executor = ToolExecutor(
            self.registry,
            ToolValidator(self.registry),
        )

    def tearDown(self):
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_create_character_executes_and_persists(self):
        result = self.executor.execute("create_character", VALID_CREATE_ARGS)
        self.assertTrue(result.success)
        self.assertEqual(result.output["name"], "Aria")
        stored = self.repository.get(UUID(result.output["id"]))
        self.assertIsNotNone(stored)
        self.assertEqual(stored.name, "Aria")

    def test_get_character_executes(self):
        created = self.executor.execute("create_character", VALID_CREATE_ARGS)
        result = self.executor.execute(
            "get_character",
            {"character_id": created.output["id"]},
        )
        self.assertTrue(result.success)
        self.assertEqual(result.output["id"], created.output["id"])

    def test_update_character_executes(self):
        created = self.executor.execute("create_character", VALID_CREATE_ARGS)
        result = self.executor.execute(
            "update_character",
            {"character_id": created.output["id"], "level": 5},
        )
        self.assertTrue(result.success)
        self.assertEqual(result.output["level"], 5)

    def test_delete_character_executes(self):
        created = self.executor.execute("create_character", VALID_CREATE_ARGS)
        result = self.executor.execute(
            "delete_character",
            {"character_id": created.output["id"]},
        )
        self.assertTrue(result.success)
        self.assertEqual(
            result.output,
            {"deleted": True, "character_id": created.output["id"]},
        )

    def test_invalid_uuid_returns_predictable_failure(self):
        result = self.executor.execute(
            "get_character",
            {"character_id": INVALID_ID},
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_handler_error")
        self.assertIn("UUID", result.error.message)

    def test_missing_character_returns_predictable_failure(self):
        result = self.executor.execute(
            "get_character",
            {"character_id": MISSING_ID},
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_handler_error")
        self.assertEqual(result.error.message, "Character not found")

    def test_hp_greater_than_max_hp_domain_validation_failure(self):
        args = dict(VALID_CREATE_ARGS)
        args["hp"] = 99
        args["max_hp"] = 12
        result = self.executor.execute("create_character", args)
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_domain_validation_error")

    def test_level_over_20_fails_before_handler(self):
        args = dict(VALID_CREATE_ARGS)
        args["level"] = 21
        # Spy by wrapping create_character
        original = self.tools.create_character
        calls = []

        def wrapper(**kwargs):
            calls.append(kwargs)
            return original(**kwargs)

        self.registry = ToolRegistry()
        tools = CharacterTools(self.repository)
        tools.create_character = wrapper  # type: ignore[method-assign]
        for binding in character_tool_bindings(tools):
            self.registry.register(binding)
        executor = ToolExecutor(self.registry, ToolValidator(self.registry))

        result = executor.execute("create_character", args)
        self.assertFalse(result.success)
        self.assertEqual(result.error.code, "tool_validation_error")
        self.assertEqual(calls, [])


class ToolExecutionSourceSafetyTests(unittest.TestCase):
    def test_execution_module_has_no_generic_except(self):
        import app.tools.execution as execution_module

        source = inspect.getsource(execution_module)
        self.assertNotIn("except Exception", source)
        self.assertNotIn("except BaseException", source)

    def test_execution_module_has_no_provider_imports(self):
        import app.tools.execution as execution_module

        source = inspect.getsource(execution_module)
        for forbidden in (
            "OpenAI",
            "responses.create",
            "LLMService",
            "Settings",
            "FastAPI",
            "app.main",
            "CharacterRepository",
            "CharacterTools",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
