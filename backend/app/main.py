"""
Minimal FastAPI entry point for DnD AI Game Platform.

WHY this file exists:
- FastAPI needs one place where the application object is created.
- Routes (endpoints) are registered on that object.
- Later stages will grow this into routers, services, DB, and AI tools.
- During the early character stage, the few routes stay in one readable file.
"""

from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.errors import (
    CharacterNotFoundError,
    character_not_found_handler,
    validation_error_response,
)
from app.models.character import Character
from app.persistence.db import create_engine_for_url, create_session_factory
from app.persistence.models import Base
from app.persistence.repository import CharacterRepository
from app.schemas.character import CharacterCreate, CharacterResponse, CharacterUpdate

# Create the application instance.
# title/version show up in auto-generated docs at /docs once the server runs.
app = FastAPI(
    title="DnD AI Game Platform",
    version="0.1.0",
)

engine = create_engine_for_url()
session_factory = create_session_factory(engine)
Base.metadata.create_all(bind=engine)
character_repository = CharacterRepository(session_factory)

app.add_exception_handler(CharacterNotFoundError, character_not_found_handler)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
):
    return validation_error_response(exc.errors())


@app.get("/")
def root():
    """
    Root endpoint — quick proof that the API is alive.
    Returns basic project identity for humans and simple health checks.
    """
    return {
        "name": "DnD AI Game Platform",
        "version": "0.1.0",
        "message": "Backend is running",
    }


@app.get("/health")
def health():
    """
    Health endpoint — used by monitoring and future Docker/orchestration.
    Keep this lightweight: no DB or AI calls here.
    """
    return {"status": "ok"}


@app.post(
    "/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_character(character_data: CharacterCreate) -> CharacterResponse:
    """Create, persist, and return a character."""
    character = Character(**character_data.model_dump())
    persisted = character_repository.create(character)
    return CharacterResponse.model_validate(persisted)


@app.get("/characters", response_model=list[CharacterResponse])
def list_characters() -> list[CharacterResponse]:
    """Return all persisted characters."""
    return [CharacterResponse.model_validate(c) for c in character_repository.list()]


@app.get("/characters/{character_id}", response_model=CharacterResponse)
def get_character(character_id: UUID) -> CharacterResponse:
    """Return one character by id or 404."""
    character = character_repository.get(character_id)
    if character is None:
        raise CharacterNotFoundError()
    return CharacterResponse.model_validate(character)


@app.patch("/characters/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: UUID,
    character_update: CharacterUpdate,
) -> CharacterResponse | JSONResponse:
    """Patch only provided fields while preserving Character invariants."""
    existing_character = character_repository.get(character_id)
    if existing_character is None:
        raise CharacterNotFoundError()

    updated_values = character_update.model_dump(exclude_unset=True)
    merged_payload = existing_character.model_dump() | updated_values

    # Locally convert expected domain validation failures to the shared 422
    # contract. Do not register a global ValidationError handler — unexpected
    # Pydantic errors elsewhere should remain server failures.
    try:
        updated_character = Character(**merged_payload)
    except ValidationError as exc:
        return validation_error_response(exc.errors())

    persisted = character_repository.update(updated_character)
    if persisted is None:
        raise CharacterNotFoundError()
    return CharacterResponse.model_validate(persisted)


@app.delete("/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(character_id: UUID) -> Response:
    """Delete character by id or return 404."""
    deleted = character_repository.delete(character_id)
    if not deleted:
        raise CharacterNotFoundError()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
