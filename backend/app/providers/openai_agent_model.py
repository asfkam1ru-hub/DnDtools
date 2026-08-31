"""
OpenAI Responses adapter for provider-neutral agent steps (Phase 3, Step 3.10).

Owns OpenAI wire-format translation:
- ToolDefinition → Responses tools schema
- AgentMessage transcript → Responses input items
- Responses output → AgentModelResponse / ToolCallProposal
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from openai import OpenAI

from app.agent.contracts import (
    AgentMessage,
    AgentModelResponse,
    ToolCallProposal,
)
from app.config import Settings
from app.providers.base import LLMConfigurationError, LLMResponseError
from app.tools.schema import ToolDefinition


class OpenAIAgentModel:
    """AgentModel implementation using the OpenAI Responses API."""

    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        self._settings = settings
        self._client = client

    def complete(
        self,
        messages: Sequence[AgentMessage],
        *,
        tools: Sequence[ToolDefinition] | None = None,
    ) -> AgentModelResponse:
        api_key = self._require_api_key()
        client = self._get_client(api_key)

        request_kwargs: dict[str, Any] = {
            "model": self._settings.llm_model,
            "input": agent_messages_to_openai_input(messages),
        }
        if tools:
            request_kwargs["tools"] = tool_definitions_to_openai_tools(tools)

        response = client.responses.create(**request_kwargs)
        return openai_response_to_agent_model_response(response)

    def _require_api_key(self) -> str:
        raw_key = self._settings.openai_api_key
        if raw_key is None or not str(raw_key).strip():
            raise LLMConfigurationError(
                "OPENAI_API_KEY is required to use the OpenAI agent model"
            )
        return str(raw_key).strip()

    def _get_client(self, api_key: str) -> OpenAI:
        if self._client is not None:
            return self._client
        return OpenAI(api_key=api_key)


def tool_definitions_to_openai_tools(
    tools: Sequence[ToolDefinition],
) -> list[dict[str, Any]]:
    """
    Translate provider-neutral ToolDefinition objects to OpenAI Responses tools.

    Each tool becomes:
    {"type": "function", "name": ..., "description": ..., "parameters": ...}
    """
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in tools
    ]


def agent_messages_to_openai_input(
    messages: Sequence[AgentMessage],
) -> list[dict[str, Any]]:
    """Translate agent transcript messages to OpenAI Responses input items."""
    items: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "assistant" and message.tool_call_proposal is not None:
            items.append(_tool_call_proposal_to_openai_function_call(
                message.tool_call_proposal
            ))
            if message.content.strip():
                items.append({"role": "assistant", "content": message.content})
            continue

        if message.role == "tool":
            if not message.tool_call_id or not str(message.tool_call_id).strip():
                raise LLMResponseError(
                    "Tool transcript message missing provider-neutral tool_call_id"
                )
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": message.tool_call_id,
                    "output": message.content,
                }
            )
            continue

        items.append({"role": message.role, "content": message.content})
    return items


def openai_response_to_agent_model_response(response: object) -> AgentModelResponse:
    """Parse an OpenAI Responses object into a provider-neutral model step."""
    tool_call = _extract_tool_call_proposal(response)
    content = _extract_assistant_content(response)
    if tool_call is not None:
        return AgentModelResponse(content=content, tool_call=tool_call)
    if not content.strip():
        raise LLMResponseError("LLM response did not contain usable text")
    return AgentModelResponse(content=content, tool_call=None)


def _tool_call_proposal_to_openai_function_call(
    proposal: ToolCallProposal,
) -> dict[str, Any]:
    arguments = proposal.arguments
    if isinstance(arguments, dict):
        arguments_payload = json.dumps(arguments)
    elif isinstance(arguments, str):
        arguments_payload = arguments
    else:
        raise LLMResponseError(
            "ToolCallProposal arguments must be a JSON object or JSON string"
        )

    return {
        "type": "function_call",
        "name": proposal.name,
        "call_id": proposal.call_id,
        "arguments": arguments_payload,
    }


def _extract_tool_call_proposal(response: object) -> ToolCallProposal | None:
    output = _read_field(response, "output")
    if not isinstance(output, list):
        return None

    for item in output:
        item_type = _read_field(item, "type")
        if item_type != "function_call":
            continue

        name = _read_field(item, "name")
        if not isinstance(name, str) or not name.strip():
            raise LLMResponseError("OpenAI function_call item missing tool name")

        call_id = _read_field(item, "call_id")
        if not isinstance(call_id, str) or not call_id.strip():
            raise LLMResponseError("OpenAI function_call item missing call_id")

        arguments = _parse_tool_arguments(_read_field(item, "arguments"))
        return ToolCallProposal(name=name, call_id=call_id, arguments=arguments)

    return None


def _extract_assistant_content(response: object) -> str:
    output_text = _read_field(response, "output_text")
    if isinstance(output_text, str):
        return output_text

    output = _read_field(response, "output")
    if not isinstance(output, list):
        return ""

    text_parts: list[str] = []
    for item in output:
        item_type = _read_field(item, "type")
        if item_type in {"message", "output_text"}:
            content = _read_field(item, "content")
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    part_text = _read_field(part, "text")
                    if isinstance(part_text, str):
                        text_parts.append(part_text)

    return "".join(text_parts)


def _parse_tool_arguments(raw_arguments: object) -> object:
    if raw_arguments is None:
        raise LLMResponseError("OpenAI function_call item missing arguments")

    if isinstance(raw_arguments, str):
        if not raw_arguments.strip():
            raise LLMResponseError("OpenAI function_call arguments were empty")
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                "OpenAI function_call arguments were not valid JSON"
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMResponseError(
                "OpenAI function_call arguments must decode to a JSON object"
            )
        return parsed

    if isinstance(raw_arguments, Mapping):
        return dict(raw_arguments)

    raise LLMResponseError(
        "OpenAI function_call arguments must be a JSON object or JSON string"
    )


def _read_field(value: object, key: str) -> object:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)
