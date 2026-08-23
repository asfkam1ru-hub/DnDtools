import unittest
from unittest.mock import MagicMock

from app.tools.character import (
    CREATE_CHARACTER_TOOL,
    DELETE_CHARACTER_TOOL,
    GET_CHARACTER_TOOL,
    LIST_CHARACTERS_TOOL,
    UPDATE_CHARACTER_TOOL,
    character_tool_bindings,
)
from app.tools.registry import (
    DuplicateToolError,
    ToolBinding,
    ToolNotRegisteredError,
    ToolRegistry,
)
from app.tools.schema import ToolDefinition


def make_definition(name: str) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"{name} tool",
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )


class ToolRegistryTests(unittest.TestCase):
    def test_tool_binding_stores_definition_and_handler(self):
        handler = MagicMock(name="handler")
        definition = make_definition("demo_tool")
        binding = ToolBinding(definition=definition, handler=handler)

        self.assertIs(binding.definition, definition)
        self.assertIs(binding.handler, handler)

    def test_register_and_get_returns_same_binding(self):
        registry = ToolRegistry()
        binding = ToolBinding(make_definition("alpha"), MagicMock())
        registry.register(binding)

        self.assertIs(registry.get("alpha"), binding)

    def test_definitions_returns_registered_definitions(self):
        registry = ToolRegistry()
        first = ToolBinding(make_definition("one"), MagicMock())
        second = ToolBinding(make_definition("two"), MagicMock())
        registry.register(first)
        registry.register(second)

        self.assertEqual(
            registry.definitions(),
            [first.definition, second.definition],
        )

    def test_registration_order_is_preserved(self):
        registry = ToolRegistry()
        names = ["first", "second", "third"]
        for name in names:
            registry.register(ToolBinding(make_definition(name), MagicMock()))

        self.assertEqual(registry.names(), names)
        self.assertEqual(
            [item.name for item in registry.definitions()],
            names,
        )

    def test_duplicate_name_is_rejected(self):
        registry = ToolRegistry()
        registry.register(ToolBinding(make_definition("dup"), MagicMock()))

        with self.assertRaises(DuplicateToolError):
            registry.register(ToolBinding(make_definition("dup"), MagicMock()))

    def test_unknown_tool_lookup_raises_registry_error(self):
        registry = ToolRegistry()
        with self.assertRaises(ToolNotRegisteredError):
            registry.get("missing")

    def test_two_different_tools_can_be_registered(self):
        registry = ToolRegistry()
        registry.register(ToolBinding(make_definition("a"), MagicMock()))
        registry.register(ToolBinding(make_definition("b"), MagicMock()))

        self.assertIn("a", registry)
        self.assertIn("b", registry)
        self.assertEqual(len(registry.definitions()), 2)

    def test_handler_is_not_called_on_register_get_or_definitions(self):
        handler = MagicMock()
        registry = ToolRegistry()
        binding = ToolBinding(make_definition("quiet"), handler)

        registry.register(binding)
        registry.get("quiet")
        registry.definitions()

        handler.assert_not_called()

    def test_registry_has_no_public_execution_methods(self):
        public_names = {
            name for name in dir(ToolRegistry) if not name.startswith("_")
        }
        self.assertTrue(
            {"execute", "dispatch", "invoke", "run"}.isdisjoint(public_names)
        )

    def test_character_tool_bindings_cover_all_five_definitions(self):
        tools = MagicMock()
        bindings = character_tool_bindings(tools)

        self.assertEqual(len(bindings), 5)
        self.assertEqual(
            [binding.definition.name for binding in bindings],
            [
                "get_character",
                "list_characters",
                "create_character",
                "update_character",
                "delete_character",
            ],
        )

    def test_character_bindings_use_expected_definitions(self):
        tools = MagicMock()
        bindings = character_tool_bindings(tools)
        by_name = {binding.definition.name: binding for binding in bindings}

        self.assertIs(by_name["get_character"].definition, GET_CHARACTER_TOOL)
        self.assertIs(by_name["list_characters"].definition, LIST_CHARACTERS_TOOL)
        self.assertIs(by_name["create_character"].definition, CREATE_CHARACTER_TOOL)
        self.assertIs(by_name["update_character"].definition, UPDATE_CHARACTER_TOOL)
        self.assertIs(by_name["delete_character"].definition, DELETE_CHARACTER_TOOL)

    def test_character_bindings_use_expected_handlers(self):
        tools = MagicMock()
        bindings = character_tool_bindings(tools)
        by_name = {binding.definition.name: binding for binding in bindings}

        self.assertIs(by_name["get_character"].handler, tools.get_character)
        self.assertIs(by_name["list_characters"].handler, tools.list_characters)
        self.assertIs(by_name["create_character"].handler, tools.create_character)
        self.assertIs(by_name["update_character"].handler, tools.update_character)
        self.assertIs(by_name["delete_character"].handler, tools.delete_character)

    def test_registering_character_bindings_yields_five_definitions(self):
        registry = ToolRegistry()
        tools = MagicMock()
        for binding in character_tool_bindings(tools):
            registry.register(binding)

        self.assertEqual(len(registry.definitions()), 5)
        self.assertEqual(
            [item.name for item in registry.definitions()],
            [
                "get_character",
                "list_characters",
                "create_character",
                "update_character",
                "delete_character",
            ],
        )

    def test_bindings_are_provider_neutral(self):
        tools = MagicMock()
        for binding in character_tool_bindings(tools):
            dumped = binding.definition.model_dump()
            self.assertEqual(
                set(dumped.keys()),
                {"name", "description", "parameters"},
            )
            self.assertNotIn("function", dumped)


if __name__ == "__main__":
    unittest.main()
