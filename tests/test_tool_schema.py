import unittest

from pydantic import ValidationError

from app.tools.schema import ToolDefinition


VALID_PARAMETERS = {
    "type": "object",
    "properties": {
        "character_id": {
            "type": "string",
        }
    },
    "required": ["character_id"],
    "additionalProperties": False,
}


def make_tool(**overrides) -> ToolDefinition:
    data = {
        "name": "get_character",
        "description": "Get a character by id",
        "parameters": VALID_PARAMETERS,
    }
    data.update(overrides)
    return ToolDefinition(**data)


class ToolSchemaTests(unittest.TestCase):
    def test_valid_tool_definition_is_created(self):
        tool = make_tool()
        self.assertEqual(tool.name, "get_character")
        self.assertEqual(tool.description, "Get a character by id")
        self.assertEqual(tool.parameters["type"], "object")

    def test_model_dump_contains_core_fields(self):
        dumped = make_tool().model_dump()
        self.assertEqual(
            set(dumped.keys()),
            {"name", "description", "parameters"},
        )

    def test_empty_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(name="")

    def test_whitespace_only_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(name="   ")

    def test_invalid_name_characters_are_rejected(self):
        for invalid_name in ("get character", "get.character", "get/character", "tool!"):
            with self.subTest(name=invalid_name):
                with self.assertRaises(ValidationError):
                    make_tool(name=invalid_name)

    def test_empty_description_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(description="")

    def test_whitespace_only_description_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(description="   ")

    def test_parameters_without_object_type_are_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(
                parameters={
                    "type": "string",
                    "properties": {},
                }
            )

    def test_properties_must_be_dict(self):
        with self.assertRaises(ValidationError):
            make_tool(
                parameters={
                    "type": "object",
                    "properties": ["character_id"],
                }
            )

    def test_required_must_be_list_of_strings(self):
        with self.assertRaises(ValidationError):
            make_tool(
                parameters={
                    "type": "object",
                    "properties": {"character_id": {"type": "string"}},
                    "required": "character_id",
                }
            )

        with self.assertRaises(ValidationError):
            make_tool(
                parameters={
                    "type": "object",
                    "properties": {"character_id": {"type": "string"}},
                    "required": [1],
                }
            )

    def test_required_name_missing_from_properties_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_tool(
                parameters={
                    "type": "object",
                    "properties": {"character_id": {"type": "string"}},
                    "required": ["missing_field"],
                }
            )

    def test_valid_required_and_properties_are_accepted(self):
        tool = make_tool(
            parameters={
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "include_inventory": {"type": "boolean"},
                },
                "required": ["character_id"],
                "additionalProperties": False,
            }
        )
        self.assertEqual(tool.parameters["required"], ["character_id"])
        self.assertIn("include_inventory", tool.parameters["properties"])

    def test_additional_properties_false_is_preserved(self):
        dumped = make_tool().model_dump()
        self.assertIs(dumped["parameters"]["additionalProperties"], False)

    def test_schema_is_provider_neutral(self):
        dumped = make_tool().model_dump()
        self.assertNotIn("function", dumped)
        self.assertNotIn("type", dumped)  # no OpenAI {"type":"function"} wrapper
        self.assertEqual(set(dumped.keys()), {"name", "description", "parameters"})


if __name__ == "__main__":
    unittest.main()
