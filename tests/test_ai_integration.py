"""Offline AI stack integration tests (Phase 3, Step 3.10)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.config import Settings
from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.providers.factory import create_llm_provider, create_openai_agent_model
from app.services.agent import AgentService
from app.services.llm import LLMService
from app.tools.character import (
    CREATE_CHARACTER_TOOL,
    CharacterTools,
    character_tool_bindings,
)
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry
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


def make_settings(**overrides) -> Settings:
    data = {
        "app_env": "development",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "openai_api_key": "test-key-not-real",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def make_text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(output_text=text)


def make_tool_call_response(
    name: str,
    arguments: dict,
    *,
    call_id: str = "call_123",
    content: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        output_text=content,
        output=[
            SimpleNamespace(
                type="function_call",
                name=name,
                arguments=json.dumps(arguments),
                call_id=call_id,
            )
        ],
    )


class QueuedOpenAIClient:
    """Fake OpenAI client returning scripted Responses API payloads."""

    def __init__(self, scripted_responses):
        self._scripted = list(scripted_responses)
        self.create_calls: list[dict] = []
        self.responses = self._ResponsesProxy(self)

    class _ResponsesProxy:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.create_calls.append(kwargs)
            if not self._outer._scripted:
                raise AssertionError("No scripted OpenAI responses left")
            return self._outer._scripted.pop(0)


class AIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_ai_integration.db"
        self._engine = create_engine_for_url(f"sqlite:///{db_path}")
        session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)
        self.repository = CharacterRepository(session_factory)
        self.tools = CharacterTools(self.repository)
        self.registry = ToolRegistry()
        for binding in character_tool_bindings(self.tools):
            self.registry.register(binding)
        self.executor = ToolExecutor(self.registry, ToolValidator(self.registry))
        self.settings = make_settings()
        self.llm_service = LLMService(create_llm_provider(self.settings, client=MagicMock()))

    def tearDown(self):
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def _build_agent(self, client) -> AgentService:
        model = create_openai_agent_model(self.settings, client=client)
        return AgentService(
            self.llm_service,
            self.executor,
            model=model,
            max_tool_steps=3,
        )

    def test_text_only_openai_path_does_not_invoke_character_handlers(self):
        handler_spy = MagicMock(side_effect=self.tools.create_character)
        self.tools.create_character = handler_spy  # type: ignore[method-assign]

        client = QueuedOpenAIClient([make_text_response("The tavern is quiet.")])
        agent = self._build_agent(client)

        result = agent.run_turn(
            "Describe the tavern",
            tool_definitions=self.registry.definitions(),
        )

        self.assertEqual(result.final_content, "The tavern is quiet.")
        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(result.tool_steps_used, 0)
        handler_spy.assert_not_called()

    def test_one_openai_tool_proposal_persists_character_and_completes(self):
        client = QueuedOpenAIClient(
            [
                make_tool_call_response(
                    "create_character",
                    VALID_CREATE_ARGS,
                    content="Creating character",
                ),
                make_text_response("Character ready"),
            ]
        )
        agent = self._build_agent(client)

        result = agent.run_turn(
            "Create Aria",
            tool_definitions=self.registry.definitions(),
        )

        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(result.final_content, "Character ready")
        self.assertEqual(result.tool_steps_used, 1)
        self.assertTrue(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].output["name"], "Aria")
        stored = self.repository.get(UUID(result.tool_results[0].output["id"]))
        self.assertIsNotNone(stored)
        self.assertEqual(len(client.create_calls), 2)
        self.assertIn("tools", client.create_calls[0])
        second_input = client.create_calls[1]["input"]
        function_call_items = [
            item for item in second_input if item.get("type") == "function_call"
        ]
        output_items = [
            item for item in second_input if item.get("type") == "function_call_output"
        ]
        self.assertEqual(len(function_call_items), 1)
        self.assertEqual(len(output_items), 1)
        self.assertEqual(function_call_items[0]["name"], "create_character")
        self.assertEqual(function_call_items[0]["call_id"], "call_123")
        self.assertEqual(output_items[0]["call_id"], "call_123")
        self.assertNotEqual(
            function_call_items[0]["call_id"],
            function_call_items[0]["name"],
        )
        tool_message = result.messages[-2]
        self.assertEqual(tool_message.role, "tool")
        self.assertEqual(tool_message.tool_call_id, "call_123")
        self.assertEqual(tool_message.tool_name, "create_character")

    def test_validation_failure_is_controlled_and_turn_can_complete(self):
        client = QueuedOpenAIClient(
            [
                make_tool_call_response(
                    "create_character",
                    {"name": "Bad"},
                    content="Bad create",
                ),
                make_text_response("Validation noted"),
            ]
        )
        agent = self._build_agent(client)

        result = agent.run_turn(
            "Create invalid character",
            tool_definitions=self.registry.definitions(),
        )

        self.assertEqual(result.stopped_reason, "completed")
        self.assertFalse(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].error.code, "tool_validation_error")
        self.assertEqual(result.final_content, "Validation noted")

    def test_unknown_tool_is_controlled_failure(self):
        client = QueuedOpenAIClient(
            [
                make_tool_call_response("missing_tool", {}, content="Unknown"),
                make_text_response("Handled"),
            ]
        )
        agent = self._build_agent(client)

        result = agent.run_turn(
            "Call missing tool",
            tool_definitions=self.registry.definitions(),
        )

        self.assertFalse(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].error.code, "tool_validation_error")
        self.assertEqual(result.final_content, "Handled")

    def test_unexpected_handler_exception_propagates(self):
        from app.tools.registry import ToolBinding
        from app.tools.schema import ToolDefinition

        def boom(**_kwargs):
            raise RuntimeError("database invariant broken")

        registry = ToolRegistry()
        registry.register(
            ToolBinding(
                ToolDefinition(
                    name="boom_tool",
                    description="Raises unexpectedly",
                    parameters={
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                boom,
            )
        )
        executor = ToolExecutor(registry, ToolValidator(registry))
        client = QueuedOpenAIClient(
            [
                make_tool_call_response("boom_tool", {}, content="Boom"),
            ]
        )
        agent = AgentService(
            self.llm_service,
            executor,
            model=create_openai_agent_model(self.settings, client=client),
        )

        with self.assertRaises(RuntimeError) as ctx:
            agent.run_turn(
                "Trigger boom",
                tool_definitions=registry.definitions(),
            )
        self.assertEqual(str(ctx.exception), "database invariant broken")

    def test_max_tool_steps_blocks_second_execution(self):
        client = QueuedOpenAIClient(
            [
                make_tool_call_response(
                    "create_character",
                    VALID_CREATE_ARGS,
                    content="First",
                ),
                make_tool_call_response(
                    "create_character",
                    {**VALID_CREATE_ARGS, "name": "Second"},
                    content="Second blocked",
                ),
            ]
        )
        agent = AgentService(
            self.llm_service,
            self.executor,
            model=create_openai_agent_model(self.settings, client=client),
            max_tool_steps=1,
        )

        result = agent.run_turn(
            "Create characters",
            tool_definitions=self.registry.definitions(),
        )

        self.assertEqual(result.stopped_reason, "max_tool_steps")
        self.assertEqual(result.tool_steps_used, 1)
        self.assertEqual(len(result.tool_results), 1)
        self.assertEqual(result.final_content, "Second blocked")

    def test_tool_schemas_forwarded_on_first_openai_call(self):
        client = QueuedOpenAIClient([make_text_response("ok")])
        agent = self._build_agent(client)
        tool_definitions = self.registry.definitions()

        agent.run_turn("Hi", tool_definitions=tool_definitions)

        first_call = client.create_calls[0]
        self.assertIn("tools", first_call)
        tool_names = {item["name"] for item in first_call["tools"]}
        self.assertIn(CREATE_CHARACTER_TOOL.name, tool_names)

    def test_no_openai_api_key_env_required_when_client_injected(self):
        settings = make_settings(openai_api_key="injected-client-key")
        client = QueuedOpenAIClient([make_text_response("ok")])
        model = create_openai_agent_model(settings, client=client)

        from app.agent.contracts import AgentMessage

        result = model.complete([AgentMessage(role="user", content="Hi")])
        self.assertEqual(result.content, "ok")
        self.assertEqual(len(client.create_calls), 1)


if __name__ == "__main__":
    unittest.main()
