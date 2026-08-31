"""Tests for provider-neutral AgentService (Phase 3, Step 3.9)."""

from __future__ import annotations

import inspect
import unittest
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.services import AgentService
from app.services.agent import (
    AgentMessage,
    AgentModelResponse,
    AgentTurnResult,
    ToolCallProposal,
)
from app.services.llm import LLMService
from app.tools.character import CharacterTools, character_tool_bindings
from app.tools.errors import ToolHandlerError
from app.tools.execution import ToolExecutor
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


class ScriptedAgentModel:
    """Deterministic stub that returns pre-scripted AgentModelResponse values."""

    def __init__(self, responses: Sequence[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[tuple[AgentMessage, ...], object]] = []

    def complete(
        self,
        messages: Sequence[AgentMessage],
        *,
        tools: Sequence[ToolDefinition] | None = None,
    ) -> AgentModelResponse:
        self.calls.append((tuple(messages), tools))
        if not self._responses:
            raise AssertionError("ScriptedAgentModel has no remaining responses")
        return self._responses.pop(0)


def make_definition(name: str, parameters: dict) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"{name} tool",
        parameters=parameters,
    )


def build_demo_executor(handler) -> tuple[ToolExecutor, MagicMock]:
    registry = ToolRegistry()
    registry.register(
        ToolBinding(
            make_definition(
                "demo_tool",
                {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string", "minLength": 1},
                    },
                    "required": ["character_id"],
                    "additionalProperties": False,
                },
            ),
            handler,
        )
    )
    return ToolExecutor(registry, ToolValidator(registry)), handler


class AgentServiceTests(unittest.TestCase):
    def test_agent_service_importable_from_services_package(self):
        self.assertTrue(callable(AgentService))

    def test_no_tool_turn_success_via_llm_service(self):
        provider = MagicMock()
        provider.generate.return_value = "The tavern is quiet."
        executor, handler = build_demo_executor(MagicMock(return_value={"ok": True}))
        agent = AgentService(LLMService(provider), executor)

        result = agent.run_turn("Describe the tavern")

        self.assertIsInstance(result, AgentTurnResult)
        self.assertEqual(result.final_content, "The tavern is quiet.")
        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(result.tool_steps_used, 0)
        self.assertEqual(result.tool_results, ())
        handler.assert_not_called()
        provider.generate.assert_called_once()

    def test_one_valid_tool_call_routed_through_executor(self):
        handler = MagicMock(return_value={"ok": True, "id": "abc"})
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Calling tool",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_1",
                        arguments={"character_id": "abc"},
                    ),
                ),
                AgentModelResponse(content="Done with tool result", tool_call=None),
            ]
        )
        agent = AgentService(
            LLMService(MagicMock()),
            executor,
            model=model,
        )

        result = agent.run_turn("Use the tool")

        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(result.final_content, "Done with tool result")
        self.assertEqual(result.tool_steps_used, 1)
        self.assertEqual(len(result.tool_results), 1)
        self.assertTrue(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].output, {"ok": True, "id": "abc"})
        handler.assert_called_once_with(character_id="abc")
        self.assertEqual(len(model.calls), 2)
        # Second model call must include the tool result message.
        second_messages = model.calls[1][0]
        self.assertEqual(second_messages[-1].role, "tool")
        self.assertEqual(second_messages[-1].tool_name, "demo_tool")
        self.assertEqual(second_messages[-1].tool_call_id, "call_demo_1")

    def test_tool_validation_failure_does_not_invoke_handler(self):
        handler = MagicMock(return_value={"ok": True})
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Bad args",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_bad",
                        arguments={"character_id": 123},
                    ),
                ),
                AgentModelResponse(content="Recovered", tool_call=None),
            ]
        )
        agent = AgentService(LLMService(MagicMock()), executor, model=model)

        result = agent.run_turn("Bad tool call")

        handler.assert_not_called()
        self.assertEqual(result.tool_steps_used, 1)
        self.assertFalse(result.tool_results[0].success)
        self.assertEqual(
            result.tool_results[0].error.code,
            "tool_validation_error",
        )
        self.assertEqual(result.stopped_reason, "completed")

    def test_expected_tool_handler_failure_returns_controlled_result(self):
        handler = MagicMock(side_effect=ToolHandlerError("safe failure"))
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Try tool",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_1",
                        arguments={"character_id": "abc"},
                    ),
                ),
                AgentModelResponse(content="Noted failure", tool_call=None),
            ]
        )
        agent = AgentService(LLMService(MagicMock()), executor, model=model)

        result = agent.run_turn("Fail safely")

        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(len(result.tool_results), 1)
        self.assertFalse(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].error.code, "tool_handler_error")
        self.assertEqual(result.tool_results[0].error.message, "safe failure")

    def test_unexpected_exception_from_handler_propagates(self):
        handler = MagicMock(side_effect=RuntimeError("database invariant broken"))
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Try tool",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_1",
                        arguments={"character_id": "abc"},
                    ),
                ),
            ]
        )
        agent = AgentService(LLMService(MagicMock()), executor, model=model)

        with self.assertRaises(RuntimeError) as ctx:
            agent.run_turn("Boom")
        self.assertEqual(str(ctx.exception), "database invariant broken")

    def test_max_tool_steps_stops_further_tool_calls(self):
        handler = MagicMock(return_value={"ok": True})
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="First",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_one",
                        arguments={"character_id": "one"},
                    ),
                ),
                AgentModelResponse(
                    content="Second proposal blocked",
                    tool_call=ToolCallProposal(
                        name="demo_tool",
                        call_id="call_demo_two",
                        arguments={"character_id": "two"},
                    ),
                ),
            ]
        )
        agent = AgentService(
            LLMService(MagicMock()),
            executor,
            max_tool_steps=1,
            model=model,
        )

        result = agent.run_turn("Bound tools")

        self.assertEqual(result.stopped_reason, "max_tool_steps")
        self.assertEqual(result.tool_steps_used, 1)
        self.assertEqual(len(result.tool_results), 1)
        handler.assert_called_once_with(character_id="one")
        self.assertEqual(result.final_content, "Second proposal blocked")

    def test_unknown_tool_proposal_is_controlled_failure(self):
        handler = MagicMock(return_value={"ok": True})
        executor, _ = build_demo_executor(handler)
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Unknown",
                    tool_call=ToolCallProposal(
                        name="missing_tool",
                        call_id="call_missing",
                        arguments={},
                    ),
                ),
                AgentModelResponse(content="Handled", tool_call=None),
            ]
        )
        agent = AgentService(LLMService(MagicMock()), executor, model=model)

        result = agent.run_turn("Unknown tool")

        handler.assert_not_called()
        self.assertFalse(result.tool_results[0].success)
        self.assertEqual(
            result.tool_results[0].error.code,
            "tool_validation_error",
        )

    def test_agent_module_has_no_forbidden_imports(self):
        import app.services.agent as agent_module

        source = inspect.getsource(agent_module)
        # Strip module docstring so documentation wording cannot false-positive.
        body = source.split('"""', 2)[-1] if source.startswith('"""') else source
        for forbidden in (
            "openai",
            "CharacterTools",
            "CharacterRepository",
            "FastAPI",
            "Settings",
            "except Exception",
            "except BaseException",
            "binding.handler",
        ):
            self.assertNotIn(forbidden, body)

        module_file = inspect.getsourcefile(agent_module)
        self.assertIsNotNone(module_file)
        text = Path(module_file).read_text(encoding="utf-8")
        import_lines = [
            line
            for line in text.splitlines()
            if line.lstrip().startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        for forbidden in (
            "openai",
            "OpenAI",
            "CharacterTools",
            "CharacterRepository",
            "fastapi",
            "FastAPI",
            "Settings",
            "app.main",
        ):
            self.assertNotIn(forbidden, joined)

    def test_agent_does_not_call_binding_handler_directly(self):
        source = inspect.getsource(AgentService.run_turn)
        self.assertIn("self._tool_executor.execute", source)
        self.assertNotIn(".handler(", source)


class CharacterAgentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "test_agent_service.db"
        self._engine = create_engine_for_url(f"sqlite:///{db_path}")
        session_factory = create_session_factory(self._engine)
        Base.metadata.create_all(bind=self._engine)
        self.repository = CharacterRepository(session_factory)
        self.tools = CharacterTools(self.repository)
        self.registry = ToolRegistry()
        for binding in character_tool_bindings(self.tools):
            self.registry.register(binding)
        self.executor = ToolExecutor(self.registry, ToolValidator(self.registry))

    def tearDown(self):
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_create_character_via_agent_and_tool_executor(self):
        model = ScriptedAgentModel(
            [
                AgentModelResponse(
                    content="Creating character",
                    tool_call=ToolCallProposal(
                        name="create_character",
                        call_id="call_create_1",
                        arguments=VALID_CREATE_ARGS,
                    ),
                ),
                AgentModelResponse(content="Character ready", tool_call=None),
            ]
        )
        agent = AgentService(
            LLMService(MagicMock()),
            self.executor,
            model=model,
            max_tool_steps=1,
        )

        result = agent.run_turn(
            "Create Aria",
            tool_definitions=self.registry.definitions(),
        )

        self.assertEqual(result.stopped_reason, "completed")
        self.assertEqual(result.tool_steps_used, 1)
        self.assertTrue(result.tool_results[0].success)
        self.assertEqual(result.tool_results[0].output["name"], "Aria")
        self.assertEqual(result.final_content, "Character ready")


if __name__ == "__main__":
    unittest.main()
