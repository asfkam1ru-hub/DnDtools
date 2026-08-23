"""
Provider-neutral tool registry and binding (Phase 3, Step 3.6).

Links ToolDefinition objects to Python callables without executing them.
Argument validation and safe execution belong in later steps.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.tools.schema import ToolDefinition


class ToolRegistryError(Exception):
    """Base error for ToolRegistry structural failures."""


class DuplicateToolError(ToolRegistryError):
    """Raised when registering a tool name that already exists."""


class ToolNotRegisteredError(ToolRegistryError):
    """Raised when looking up a tool name that was never registered."""


@dataclass(frozen=True)
class ToolBinding:
    """Immutable pair of a tool schema and its Python handler."""

    definition: ToolDefinition
    handler: Callable[..., object]


class ToolRegistry:
    """
    Ordered store of ToolBinding entries keyed by tool name.

    This registry does not invoke handlers.
    """

    def __init__(self) -> None:
        self._bindings: dict[str, ToolBinding] = {}

    def register(self, binding: ToolBinding) -> None:
        name = binding.definition.name
        if name in self._bindings:
            raise DuplicateToolError(f"Tool already registered: {name!r}")
        self._bindings[name] = binding

    def get(self, name: str) -> ToolBinding:
        try:
            return self._bindings[name]
        except KeyError as exc:
            raise ToolNotRegisteredError(f"Tool not registered: {name!r}") from exc

    def definitions(self) -> list[ToolDefinition]:
        return [binding.definition for binding in self._bindings.values()]

    def names(self) -> list[str]:
        return list(self._bindings.keys())

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._bindings
