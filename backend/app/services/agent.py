"""
Provider-neutral agent orchestration (Phase 3, Step 3.9).

Coordinates bounded turns:
model response → optional tool proposal → ToolExecutor → tool result → next model step.

This module stays vendor-agnostic and domain-neutral: no vendor SDKs, no Character
tools, no web framework, no settings. Tool handlers run only through ToolExecutor.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.services.llm import LLMService
from app.tools.execution import ToolExecutionResult, ToolExecutor
from app.tools.schema import ToolDefinition


@dataclass(frozen=True)
class ToolCallProposal:
    """Provider-neutral request to invoke a registered tool."""

    name: str
    arguments: object


@dataclass(frozen=True)
class AgentMessage:
    """One message in an agent turn transcript."""

    role: str
    content: str
    tool_name: str | None = None
    tool_result: ToolExecutionResult | None = None


@dataclass(frozen=True)
class AgentModelResponse:
    """One model step: assistant text and optional single tool proposal."""

    content: str
    tool_call: ToolCallProposal | None = None


@dataclass(frozen=True)
class AgentTurnResult:
    """Outcome of a bounded agent turn."""

    final_content: str
    messages: tuple[AgentMessage, ...]
    tool_results: tuple[ToolExecutionResult, ...]
    tool_steps_used: int
    stopped_reason: str


class AgentModel(Protocol):
    """
    Provider-neutral model step interface used by AgentService.

    Concrete LLM vendors adapt their APIs behind this protocol.
    """

    def complete(
        self,
        messages: Sequence[AgentMessage],
        *,
        tools: Sequence[ToolDefinition] | None = None,
    ) -> AgentModelResponse:
        """Return the next assistant step for the given transcript."""
        ...


class LLMServiceAgentModel:
    """
    Adapter: plain LLMService text generation as agent steps (no tool proposals).

    Useful until a provider adapter implements native structured tool proposals.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def complete(
        self,
        messages: Sequence[AgentMessage],
        *,
        tools: Sequence[ToolDefinition] | None = None,
    ) -> AgentModelResponse:
        del tools  # text-only adapter ignores tool schemas
        prompt = _messages_to_prompt(messages)
        text = self._llm_service.generate(prompt)
        return AgentModelResponse(content=text, tool_call=None)


class AgentService:
    """Bounded orchestration between an AgentModel and ToolExecutor."""

    def __init__(
        self,
        llm_service: LLMService,
        tool_executor: ToolExecutor,
        *,
        max_tool_steps: int = 3,
        model: AgentModel | None = None,
    ) -> None:
        if max_tool_steps < 0:
            raise ValueError("max_tool_steps must be >= 0")
        self._tool_executor = tool_executor
        self._max_tool_steps = max_tool_steps
        self._model: AgentModel = (
            model if model is not None else LLMServiceAgentModel(llm_service)
        )

    def run_turn(
        self,
        user_message: str,
        *,
        system_message: str | None = None,
        tool_definitions: Sequence[ToolDefinition] | None = None,
    ) -> AgentTurnResult:
        messages: list[AgentMessage] = []
        if system_message is not None:
            messages.append(AgentMessage(role="system", content=system_message))
        messages.append(AgentMessage(role="user", content=user_message))

        tool_results: list[ToolExecutionResult] = []
        tool_steps_used = 0

        while True:
            response = self._model.complete(
                messages,
                tools=tool_definitions,
            )
            messages.append(
                AgentMessage(role="assistant", content=response.content)
            )

            if response.tool_call is None:
                return AgentTurnResult(
                    final_content=response.content,
                    messages=tuple(messages),
                    tool_results=tuple(tool_results),
                    tool_steps_used=tool_steps_used,
                    stopped_reason="completed",
                )

            if tool_steps_used >= self._max_tool_steps:
                return AgentTurnResult(
                    final_content=response.content,
                    messages=tuple(messages),
                    tool_results=tuple(tool_results),
                    tool_steps_used=tool_steps_used,
                    stopped_reason="max_tool_steps",
                )

            # Controlled path only — unexpected exceptions propagate.
            execution = self._tool_executor.execute(
                response.tool_call.name,
                response.tool_call.arguments,
            )
            tool_results.append(execution)
            tool_steps_used += 1
            messages.append(
                AgentMessage(
                    role="tool",
                    content=_tool_result_content(execution),
                    tool_name=execution.tool_name,
                    tool_result=execution,
                )
            )


def _messages_to_prompt(messages: Sequence[AgentMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        if message.role == "system":
            parts.append(f"System: {message.content}")
        elif message.role == "user":
            parts.append(f"User: {message.content}")
        elif message.role == "assistant":
            parts.append(f"Assistant: {message.content}")
        elif message.role == "tool":
            label = message.tool_name or "tool"
            parts.append(f"Tool({label}): {message.content}")
        else:
            parts.append(f"{message.role}: {message.content}")
    return "\n".join(parts)


def _tool_result_content(result: ToolExecutionResult) -> str:
    payload: dict[str, object] = {
        "tool_name": result.tool_name,
        "success": result.success,
        "output": result.output,
    }
    if result.error is not None:
        payload["error"] = {
            "code": result.error.code,
            "message": result.error.message,
        }
    else:
        payload["error"] = None
    return json.dumps(payload, ensure_ascii=True)
