"""
Minimal shared API error contract for Character endpoints.

WHY a small module:
- Keep one JSON shape for 404/422 responses.
- Avoid repeating the same HTTPException(detail=...) blocks.
"""

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.requests import Request

# Starlette 1.6 deprecates HTTP_422_UNPROCESSABLE_ENTITY in favor of
# HTTP_422_UNPROCESSABLE_CONTENT; keep numeric 422 for a stable client contract.
HTTP_422 = 422


class CharacterNotFoundError(Exception):
    """Raised when a character UUID is not present in persistence."""


def error_body(code: str, message: str, details=None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


def character_not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_body(
            code="character_not_found",
            message="Character not found",
            details=None,
        ),
    )


def validation_error_response(details) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422,
        content=error_body(
            code="validation_error",
            message="Request validation failed",
            details=jsonable_encoder(details),
        ),
    )


async def character_not_found_handler(
    _request: Request,
    _exc: CharacterNotFoundError,
) -> JSONResponse:
    return character_not_found_response()
