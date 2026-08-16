"""
Minimal FastAPI entry point for DnD AI Game Platform.

WHY this file exists:
- FastAPI needs one place where the application object is created.
- Routes (endpoints) are registered on that object.
- Later stages will grow this into routers, services, DB, and AI tools —
  but Stage 1 keeps everything in one readable file on purpose.
"""

from fastapi import FastAPI

# Create the application instance.
# title/version show up in auto-generated docs at /docs once the server runs.
app = FastAPI(
    title="DnD AI Game Platform",
    version="0.1.0",
)


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
