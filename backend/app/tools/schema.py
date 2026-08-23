"""
Provider-agnostic AI tool schema (Phase 3, Step 3.4).

Defines what a tool is — name, description, and JSON Schema parameters.
Does not execute tools or convert them to vendor-specific formats.
"""

import re
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_NAME_LENGTH = 64
_MAX_DESCRIPTION_LENGTH = 1024


class ToolDefinition(BaseModel):
    """
    Machine-readable description of one AI tool.

    `parameters` is a JSON Schema object describing tool arguments.
    Provider wrappers (vendor-specific function calling formats) belong in a later step.
    """

    name: str = Field(..., min_length=1, max_length=_MAX_NAME_LENGTH)
    description: str = Field(..., min_length=1, max_length=_MAX_DESCRIPTION_LENGTH)
    parameters: dict[str, Any]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool name must not be blank")
        if value != value.strip():
            raise ValueError("tool name must not include leading or trailing whitespace")
        if not _TOOL_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                "tool name may only contain letters, digits, underscore, and hyphen"
            )
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool description must not be blank")
        return value

    @model_validator(mode="after")
    def validate_parameters_structure(self) -> Self:
        params = self.parameters

        if params.get("type") != "object":
            raise ValueError('parameters["type"] must be "object"')

        properties = params.get("properties")
        if properties is not None and not isinstance(properties, dict):
            raise ValueError('parameters["properties"] must be an object/dict')

        required = params.get("required")
        if required is not None:
            if not isinstance(required, list) or not all(
                isinstance(item, str) for item in required
            ):
                raise ValueError('parameters["required"] must be a list of strings')

            property_names = set(properties or {})
            missing = [name for name in required if name not in property_names]
            if missing:
                raise ValueError(
                    "parameters required names must exist in properties: "
                    + ", ".join(missing)
                )

        return self
