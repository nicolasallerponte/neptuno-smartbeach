"""Webcam API router."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from data.webcams import get_webcam

router = APIRouter(tags=["webcams"])


@router.get("/beaches/{beach_id}/webcam")
async def get_beach_webcam(beach_id: str) -> dict:
    """Return webcam snapshot info for a beach, if available."""
    info = get_webcam(beach_id)
    if not info:
        return {"available": False}
    return info
