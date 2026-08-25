"""
Safe tool execution pipeline (Phase 3, Step 3.8).

Flow:
1. validate arguments
2. resolve registered binding
3. invoke bound handler once
4. ensure JSON-compatible output

Expected tool/domain failures become ToolExecutionResult(success=False).
Unexpected exceptions propagate unchanged.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.tools.errors import ToolHandlerError
from app.tools.registry import ToolRegistry
from app.tools.validation import ToolValidationError, ToolValidator


@dataclass(frozen=True)
class ToolExecutionErrorData:
    code: str
    message: str


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    success: bool
    output: object | None = None
    error: ToolExecutionErrorData | None = None


class ToolResultValidationError(Exception):
    """Raised when a handler return value is not JSON-compatible."""


class ToolExecutor:
    """Provider-neutral executor that validates, then calls registered handlers."""

    def __init__(self, registry: ToolRegistry, validator: ToolValidator) -> None:
        self._registry = registry
        self._validator = validator

    def execute(self, tool_name: str, arguments: object) -> ToolExecutionResult:
        try:
            validated_arguments = self._validator.validate(tool_name, arguments)
        except ToolValidationError as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=ToolExecutionErrorData(
                    code="tool_validation_error",
                    message=str(exc),
                ),
            )

        binding = self._registry.get(tool_name)

        try:
            raw_result = binding.handler(**validated_arguments)
        except ToolHandlerError as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=ToolExecutionErrorData(
                    code=exc.code,
                    message=str(exc),
                ),
            )
        except ValidationError as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=ToolExecutionErrorData(
                    code="tool_domain_validation_error",
                    message=_domain_validation_message(exc),
                ),
            )

        try:
            output = ensure_json_compatible(raw_result)
        except ToolResultValidationError as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=ToolExecutionErrorData(
                    code="tool_result_validation_error",
                    message=str(exc),
                ),
            )

        return ToolExecutionResult(
            tool_name=tool_name,
            success=True,
            output=output,
            error=None,
        )


def ensure_json_compatible(value: object, *, path: str = "$") -> object:
    """
    Accept only JSON-compatible values.

    bool is accepted as boolean; integer checks use exact `int` (not bool).
    """
    if value is None or isinstance(value, (str, float)):
        return value
    if type(value) is bool or type(value) is int:
        return value
    if isinstance(value, list):
        return [
            ensure_json_compatible(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ToolResultValidationError(
                    f"JSON object keys must be strings at {path}"
                )
            normalized[key] = ensure_json_compatible(item, path=f"{path}.{key}")
        return normalized

    raise ToolResultValidationError(
        f"Non JSON-compatible value at {path}: {type(value).__name__}"
    )


def _domain_validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Domain validation failed"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    message = first.get("msg", "Domain validation failed")
    if location:
        return f"{location}: {message}"
    return str(message)
