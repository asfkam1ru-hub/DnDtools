"""
Provider-neutral runtime validation for tool arguments (Phase 3, Step 3.7).

Validates tool_name + raw arguments against ToolDefinition.parameters.
Never invokes handlers — execution belongs to Step 3.8.
"""

from copy import deepcopy
from typing import Any

from app.tools.registry import ToolNotRegisteredError, ToolRegistry

_SUPPORTED_TYPES = frozenset({"string", "integer", "boolean", "array", "object"})
_IGNORED_SCHEMA_KEYS = frozenset(
    {
        "description",
        "title",
        "default",
        "examples",
    }
)


class ToolValidationError(Exception):
    """Base error for tool lookup / schema validation failures."""


class ToolArgumentsValidationError(ToolValidationError):
    """Raised when raw tool arguments fail the ToolDefinition schema."""


class UnsupportedToolSchemaError(ToolValidationError):
    """Raised when a ToolDefinition schema uses unsupported JSON Schema features."""


class ToolValidator:
    """Validate untrusted tool arguments against a ToolRegistry entry."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def validate(self, tool_name: str, arguments: object) -> dict[str, object]:
        try:
            binding = self._registry.get(tool_name)
        except ToolNotRegisteredError as exc:
            raise ToolValidationError(str(exc)) from exc

        if not isinstance(arguments, dict):
            raise ToolArgumentsValidationError(
                "Tool arguments must be a JSON object/dict"
            )

        validated = self._validate_value(
            arguments,
            binding.definition.parameters,
            path="$",
        )
        if not isinstance(validated, dict):
            raise ToolArgumentsValidationError(
                "Validated tool arguments must be a JSON object/dict"
            )
        return validated

    def _validate_value(
        self,
        value: object,
        schema: object,
        *,
        path: str,
    ) -> object:
        if not isinstance(schema, dict):
            raise UnsupportedToolSchemaError(
                f"Unsupported schema at {path}: schema must be an object"
            )

        schema_type = schema.get("type")
        if schema_type not in _SUPPORTED_TYPES:
            raise UnsupportedToolSchemaError(
                f"Unsupported schema type at {path}: {schema_type!r}"
            )

        self._reject_unsupported_keywords(schema, schema_type=schema_type, path=path)

        if schema_type == "object":
            return self._validate_object(value, schema, path=path)
        if schema_type == "string":
            return self._validate_string(value, schema, path=path)
        if schema_type == "integer":
            return self._validate_integer(value, schema, path=path)
        if schema_type == "boolean":
            return self._validate_boolean(value, path=path)
        if schema_type == "array":
            return self._validate_array(value, schema, path=path)

        raise UnsupportedToolSchemaError(
            f"Unsupported schema type at {path}: {schema_type!r}"
        )

    def _reject_unsupported_keywords(
        self,
        schema: dict[str, Any],
        *,
        schema_type: str,
        path: str,
    ) -> None:
        allowed = {
            "object": {"type", "properties", "required", "additionalProperties"},
            "string": {"type", "minLength", "maxLength"},
            "integer": {
                "type",
                "minimum",
                "maximum",
                "exclusiveMinimum",
                "exclusiveMaximum",
            },
            "boolean": {"type"},
            "array": {"type", "items"},
        }[schema_type]

        for key in schema:
            if key in allowed or key in _IGNORED_SCHEMA_KEYS:
                continue
            raise UnsupportedToolSchemaError(
                f"Unsupported schema keyword at {path}: {key!r}"
            )

    def _validate_object(
        self,
        value: object,
        schema: dict[str, Any],
        *,
        path: str,
    ) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ToolArgumentsValidationError(
                f"Expected object at {path}, got {type(value).__name__}"
            )

        properties = schema.get("properties", {})
        if properties is not None and not isinstance(properties, dict):
            raise UnsupportedToolSchemaError(
                f"Unsupported schema at {path}: properties must be an object"
            )
        properties = properties or {}

        required = schema.get("required", [])
        if required is not None and (
            not isinstance(required, list)
            or not all(isinstance(item, str) for item in required)
        ):
            raise UnsupportedToolSchemaError(
                f"Unsupported schema at {path}: required must be a list of strings"
            )
        required = required or []

        for field_name in required:
            if field_name not in value:
                raise ToolArgumentsValidationError(
                    f"Missing required argument: {field_name}"
                )

        additional = schema.get("additionalProperties", True)
        if additional not in (True, False):
            raise UnsupportedToolSchemaError(
                f"Unsupported schema at {path}: additionalProperties must be boolean"
            )

        result: dict[str, object] = {}
        for key, raw_value in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                result[key] = self._validate_value(
                    raw_value,
                    properties[key],
                    path=child_path,
                )
            elif additional is False:
                raise ToolArgumentsValidationError(
                    f"Unexpected argument: {key}"
                )
            else:
                result[key] = deepcopy(raw_value)

        return result

    def _validate_string(
        self,
        value: object,
        schema: dict[str, Any],
        *,
        path: str,
    ) -> str:
        if not isinstance(value, str):
            raise ToolArgumentsValidationError(
                f"Expected string at {path}, got {type(value).__name__}"
            )

        min_length = schema.get("minLength")
        if min_length is not None:
            if not isinstance(min_length, int) or isinstance(min_length, bool):
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: minLength must be an integer"
                )
            if len(value) < min_length:
                raise ToolArgumentsValidationError(
                    f"String at {path} is shorter than minLength {min_length}"
                )

        max_length = schema.get("maxLength")
        if max_length is not None:
            if not isinstance(max_length, int) or isinstance(max_length, bool):
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: maxLength must be an integer"
                )
            if len(value) > max_length:
                raise ToolArgumentsValidationError(
                    f"String at {path} is longer than maxLength {max_length}"
                )

        return value

    def _validate_integer(
        self,
        value: object,
        schema: dict[str, Any],
        *,
        path: str,
    ) -> int:
        # bool is a subclass of int in Python — reject it explicitly.
        if type(value) is not int:
            raise ToolArgumentsValidationError(
                f"Expected integer at {path}, got {type(value).__name__}"
            )

        minimum = schema.get("minimum")
        if minimum is not None:
            if type(minimum) is not int:
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: minimum must be an integer"
                )
            if value < minimum:
                raise ToolArgumentsValidationError(
                    f"Integer at {path} is less than minimum {minimum}"
                )

        maximum = schema.get("maximum")
        if maximum is not None:
            if type(maximum) is not int:
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: maximum must be an integer"
                )
            if value > maximum:
                raise ToolArgumentsValidationError(
                    f"Integer at {path} is greater than maximum {maximum}"
                )

        exclusive_minimum = schema.get("exclusiveMinimum")
        if exclusive_minimum is not None:
            if type(exclusive_minimum) is not int:
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: exclusiveMinimum must be an integer"
                )
            if value <= exclusive_minimum:
                raise ToolArgumentsValidationError(
                    f"Integer at {path} must be greater than {exclusive_minimum}"
                )

        exclusive_maximum = schema.get("exclusiveMaximum")
        if exclusive_maximum is not None:
            if type(exclusive_maximum) is not int:
                raise UnsupportedToolSchemaError(
                    f"Unsupported schema at {path}: exclusiveMaximum must be an integer"
                )
            if value >= exclusive_maximum:
                raise ToolArgumentsValidationError(
                    f"Integer at {path} must be less than {exclusive_maximum}"
                )

        return value

    def _validate_boolean(self, value: object, *, path: str) -> bool:
        if type(value) is not bool:
            raise ToolArgumentsValidationError(
                f"Expected boolean at {path}, got {type(value).__name__}"
            )
        return value

    def _validate_array(
        self,
        value: object,
        schema: dict[str, Any],
        *,
        path: str,
    ) -> list[object]:
        if not isinstance(value, list):
            raise ToolArgumentsValidationError(
                f"Expected array at {path}, got {type(value).__name__}"
            )

        items_schema = schema.get("items")
        if items_schema is None:
            return deepcopy(value)

        result: list[object] = []
        for index, item in enumerate(value):
            result.append(
                self._validate_value(
                    item,
                    items_schema,
                    path=f"{path}[{index}]",
                )
            )
        return result
