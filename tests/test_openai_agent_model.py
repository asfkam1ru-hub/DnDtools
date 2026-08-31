"""Unit tests for OpenAIAgentModel (Phase 3, Step 3.10)."""

from __future__ import annotations

import inspect
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.agent.contracts import AgentMessage, ToolCallProposal
from app.config import Settings
from app.providers.base import LLMResponseError
from app.providers.openai_agent_model import (
    OpenAIAgentModel,
    agent_messages_to_openai_input,
    openai_response_to_agent_model_response,
    tool_definitions_to_openai_tools,
)
from app.tools.schema import ToolDefinition


def make_settings(**overrides) -> Settings:
    data = {
        "app_env": "development",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "openai_api_key": "test-key-not-real",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


DEMO_TOOL = ToolDefinition(
    name="demo_tool",
    description="Demo tool",
    parameters={
        "type": "object",
        "properties": {
            "character_id": {"type": "string", "minLength": 1},
        },
        "required": ["character_id"],
        "additionalProperties": False,
    },
)


def make_text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(output_text=text)


def make_tool_call_response(
    name: str,
    arguments: object,
    *,
    call_id: str = "call_123",
    content: str = "",
) -> SimpleNamespace:
    if isinstance(arguments, dict):
        arguments_payload = json.dumps(arguments)
    else:
        arguments_payload = arguments
    return SimpleNamespace(
        output_text=content,
        output=[
            SimpleNamespace(
                type="function_call",
                name=name,
                arguments=arguments_payload,
                call_id=call_id,
            )
        ],
    )


class ToolDefinitionTranslationTests(unittest.TestCase):
    def test_tool_definitions_to_openai_tools_shape(self):
        translated = tool_definitions_to_openai_tools([DEMO_TOOL])
        self.assertEqual(
            translated,
            [
                {
                    "type": "function",
                    "name": "demo_tool",
                    "description": "Demo tool",
                    "parameters": DEMO_TOOL.parameters,
                }
            ],
        )


class OpenAIResponseParsingTests(unittest.TestCase):
    def test_text_only_response_has_no_tool_call(self):
        result = openai_response_to_agent_model_response(
            make_text_response("Hello there")
        )
        self.assertEqual(result.content, "Hello there")
        self.assertIsNone(result.tool_call)

    def test_function_call_response_parses_tool_proposal_and_call_id(self):
        result = openai_response_to_agent_model_response(
            make_tool_call_response(
                "create_character",
                {"name": "Aria"},
                call_id="call_123",
                content="Calling tool",
            )
        )
        self.assertEqual(result.content, "Calling tool")
        self.assertIsNotNone(result.tool_call)
        self.assertEqual(result.tool_call.name, "create_character")
        self.assertEqual(result.tool_call.call_id, "call_123")
        self.assertNotEqual(result.tool_call.call_id, result.tool_call.name)
        self.assertEqual(result.tool_call.arguments, {"name": "Aria"})

    def test_missing_call_id_raises(self):
        response = SimpleNamespace(
            output_text="",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="demo_tool",
                    arguments="{}",
                    call_id="",
                )
            ],
        )
        with self.assertRaises(LLMResponseError):
            openai_response_to_agent_model_response(response)

    def test_invalid_arguments_json_raises(self):
        response = make_tool_call_response("demo_tool", "{not-json")
        with self.assertRaises(LLMResponseError):
            openai_response_to_agent_model_response(response)

    def test_missing_text_and_tool_call_raises(self):
        with self.assertRaises(LLMResponseError):
            openai_response_to_agent_model_response(SimpleNamespace())


class OpenAIAgentModelTests(unittest.TestCase):
    def test_text_only_complete_returns_no_tool_call(self):
        client = MagicMock()
        client.responses.create.return_value = make_text_response("Plain answer")
        model = OpenAIAgentModel(make_settings(), client=client)

        result = model.complete([AgentMessage(role="user", content="Hi")])

        self.assertEqual(result.content, "Plain answer")
        self.assertIsNone(result.tool_call)
        client.responses.create.assert_called_once()
        call_kwargs = client.responses.create.call_args.kwargs
        self.assertNotIn("tools", call_kwargs)

    def test_tools_are_translated_and_forwarded(self):
        client = MagicMock()
        client.responses.create.return_value = make_text_response("ok")
        model = OpenAIAgentModel(make_settings(), client=client)

        model.complete(
            [AgentMessage(role="user", content="Use tool")],
            tools=[DEMO_TOOL],
        )

        call_kwargs = client.responses.create.call_args.kwargs
        self.assertEqual(
            call_kwargs["tools"],
            tool_definitions_to_openai_tools([DEMO_TOOL]),
        )

    def test_structured_tool_call_is_translated(self):
        client = MagicMock()
        client.responses.create.return_value = make_tool_call_response(
            "demo_tool",
            {"character_id": "abc"},
            call_id="call_abc",
        )
        model = OpenAIAgentModel(make_settings(), client=client)

        result = model.complete([AgentMessage(role="user", content="Go")])

        self.assertEqual(result.tool_call.name, "demo_tool")
        self.assertEqual(result.tool_call.call_id, "call_abc")
        self.assertEqual(result.tool_call.arguments, {"character_id": "abc"})

    def test_agent_messages_use_preserved_call_id_for_function_call_output(self):
        proposal = ToolCallProposal(
            name="create_character",
            call_id="call_123",
            arguments={"name": "Aria"},
        )
        items = agent_messages_to_openai_input(
            [
                AgentMessage(role="user", content="Hi"),
                AgentMessage(
                    role="assistant",
                    content="Creating character",
                    tool_call_proposal=proposal,
                ),
                AgentMessage(
                    role="tool",
                    content='{"success": true}',
                    tool_name="create_character",
                    tool_call_id="call_123",
                ),
            ]
        )
        self.assertEqual(
            items,
            [
                {"role": "user", "content": "Hi"},
                {
                    "type": "function_call",
                    "name": "create_character",
                    "call_id": "call_123",
                    "arguments": json.dumps({"name": "Aria"}),
                },
                {"role": "assistant", "content": "Creating character"},
                {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": '{"success": true}',
                },
            ],
        )
        self.assertNotEqual(items[1]["call_id"], items[1]["name"])

    def test_tool_message_without_call_id_raises(self):
        with self.assertRaises(LLMResponseError):
            agent_messages_to_openai_input(
                [
                    AgentMessage(
                        role="tool",
                        content='{"success": true}',
                        tool_name="create_character",
                    )
                ]
            )

    def test_adapter_module_has_no_forbidden_imports(self):
        import app.providers.openai_agent_model as module

        module_file = inspect.getsourcefile(module)
        self.assertIsNotNone(module_file)
        text = Path(module_file).read_text(encoding="utf-8")
        import_lines = [
            line
            for line in text.splitlines()
            if line.lstrip().startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        for forbidden in (
            "AgentService",
            "ToolExecutor",
            "CharacterTools",
            "CharacterRepository",
            "fastapi",
            "FastAPI",
        ):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
