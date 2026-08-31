"""Provider-neutral agent step contracts (Phase 3, Step 3.9/3.10)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.tools.execution import ToolExecutionResult
from app.tools.schema import ToolDefinition


@dataclass(frozen=True)
class ToolCallProposal:
    """Provider-neutral request to invoke a registered tool."""

    name: str
    call_id: str
    arguments: object


@dataclass(frozen=True)
class AgentMessage:
    """One message in an agent turn transcript."""

    role: str
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_call_proposal: ToolCallProposal | None = None
    tool_result: ToolExecutionResult | None = None


@dataclass(frozen=True)
class AgentModelResponse:
    """One model step: assistant text and optional single tool proposal."""

    content: str
    tool_call: ToolCallProposal | None = None


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
