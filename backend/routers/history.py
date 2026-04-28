"""History API router -- time-series data from QuantumLeap."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.quantumleap import get_beach_history

router = APIRouter(tags=["history"])


@router.get("/beaches/{beach_id}/history")
async def beach_history(beach_id: str, days: int = 7) -> dict:
    """Get last N days of historical data for a beach from QuantumLeap."""
    history = await get_beach_history(beach_id, days=days)
    return history
