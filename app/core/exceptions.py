"""Global exception handlers.

Moved out of main.py (Phase 2 of REFACTOR_PLAN.md). Registration itself
(`app.exception_handler(_InvalidId)(...)`) stays in main.py — it needs the
`app` instance — but the handler function and the exception class it's keyed
on live here.
"""
from bson.errors import InvalidId as _InvalidId
from fastapi import Request
from fastapi.responses import JSONResponse


async def invalid_id_handler(request: Request, exc: _InvalidId):  # noqa: ARG001
    """A malformed Mongo id (wrong length/format) reaches ObjectId() from many
    path params and request bodies across the codebase. Without a handler,
    bson raises InvalidId, which surfaces as a confusing HTTP 500. Convert it
    to a clean 400 in one place instead of guarding ~100 individual call sites."""
    return JSONResponse({"detail": "invalid id format"}, status_code=400)
