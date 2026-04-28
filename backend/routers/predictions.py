"""Predictions API router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.orion import get_entity, _extract_values

router = APIRouter(tags=["predictions"])


@router.get("/beaches/{beach_id}/predict")
async def beach_prediction(beach_id: str) -> dict:
    """Get water quality prediction for a beach from Orion."""
    entity = await get_entity(f"urn:ngsi-ld:WaterQualityPredicted:{beach_id}")
    if entity is None:
        return {"beachId": beach_id, "prediction": None, "message": "No prediction available yet"}
    return {"beachId": beach_id, "prediction": _extract_values(entity)}
