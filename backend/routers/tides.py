"""Tide prediction API router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.tides import tide_info

router = APIRouter(tags=["tides"])


@router.get("/beaches/{beach_id}/tide")
async def get_beach_tide(beach_id: str) -> dict:
    """Return current tide height, trend and next high/low for a beach."""
    return tide_info()
