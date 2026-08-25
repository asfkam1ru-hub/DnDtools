"""
Generic expected tool-handler errors (Phase 3, Step 3.8).

Entity-specific tools (e.g. Character) may subclass ToolHandlerError so the
execution pipeline can serialize expected failures without importing those
entity modules.
"""


class ToolHandlerError(Exception):
    """
    Expected, safe-to-serialize failure raised by a tool handler.

    Unexpected programming errors must NOT subclass this type.
    """

    code: str = "tool_handler_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
