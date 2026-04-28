"""Beaches API router."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.services.orion import get_all_beaches, get_beach_detail

logger = logging.getLogger("neptuno.routers.beaches")
router = APIRouter(tags=["beaches"])


@router.get("/beaches")
async def list_beaches() -> list[dict]:
    """List all beaches with current conditions from Orion-LD."""
    try:
        beaches = await get_all_beaches()
        return beaches or []
    except Exception as exc:
        logger.error("Failed to fetch beaches from Orion: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Orion-LD is not reachable. Make sure the FIWARE stack is running."},
        )


@router.get("/beaches/{beach_id}")
async def beach_detail(beach_id: str) -> dict:
    """Get detailed info for a single beach including all related entities."""
    try:
        detail = await get_beach_detail(beach_id)
    except Exception as exc:
        logger.error("Failed to fetch beach %s: %s", beach_id, exc)
        raise HTTPException(status_code=503, detail="Orion-LD is not reachable")
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Beach '{beach_id}' not found")
    return detail
