"""Alerts API router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.orion import get_alerts

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def list_alerts() -> list[dict]:
    """Get all active weather and safety alerts from Orion."""
    alerts = await get_alerts()
    return alerts
