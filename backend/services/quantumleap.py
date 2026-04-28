"""
QuantumLeap service client.

Provides async methods to query QuantumLeap for historical time-series
data persisted in CrateDB.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("neptuno.services.quantumleap")

QUANTUMLEAP_URL = os.getenv("QUANTUMLEAP_URL", "http://localhost:8668")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")
SERVICE_PATH = os.getenv("SERVICE_PATH", "/")
TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "fiware-service": TENANT,
        "fiware-servicepath": SERVICE_PATH,
    }


async def get_entity_history(
    entity_type: str,
    entity_id: str,
    attrs: str | None = None,
    last_n: int = 168,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Fetch time series for a single entity from QuantumLeap.

    Args:
        entity_type: NGSI-LD entity type (e.g. "SeaConditions")
        entity_id: Entity ID without the URN prefix
        attrs: Comma-separated attribute names to fetch
        last_n: Number of most recent values to return
        from_date: ISO 8601 start date filter
        to_date: ISO 8601 end date filter

    Returns:
        QuantumLeap response as dict with 'index' and attribute arrays.
    """
    urn = f"urn:ngsi-ld:{entity_type}:{entity_id}"
    url = f"{QUANTUMLEAP_URL}/v2/entities/{urn}"
    params: dict[str, Any] = {"lastN": last_n}
    if attrs:
        params["attrs"] = attrs
    if from_date:
        params["fromDate"] = from_date
    if to_date:
        params["toDate"] = to_date

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "QuantumLeap history for %s returned %s: %s",
            urn,
            resp.status_code,
            resp.text[:200],
        )
        return {}


async def get_type_history(
    entity_type: str,
    attrs: str | None = None,
    last_n: int = 100,
) -> dict[str, Any]:
    """Fetch time series for all entities of a type from QuantumLeap."""
    url = f"{QUANTUMLEAP_URL}/v2/types/{entity_type}"
    params: dict[str, Any] = {"lastN": last_n}
    if attrs:
        params["attrs"] = attrs

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "QuantumLeap type history for %s returned %s",
            entity_type,
            resp.status_code,
        )
        return {}


async def get_beach_history(
    beach_id: str,
    days: int = 7,
) -> dict[str, Any]:
    """Fetch a comprehensive history bundle for a beach.

    Returns a dict with keys for each entity type's historical data.
    """
    last_n = days * 24  # Approximate hourly readings

    sea = await get_entity_history(
        "SeaConditions",
        beach_id,
        attrs="waveHeight,wavePeriod,seaSurfaceTemperature,pH,salinity",
        last_n=last_n,
    )

    weather = await get_entity_history(
        "WeatherObserved",
        beach_id,
        attrs="temperature,windSpeed,relativeHumidity,precipitation",
        last_n=last_n,
    )

    water_quality = await get_entity_history(
        "WaterQualityObserved",
        beach_id,
        attrs="escherichiaColi,intestinalEnterococci,pH,turbidity,dissolvedOxygen",
        last_n=last_n // 12,  # Twice daily
    )

    return {
        "beachId": beach_id,
        "days": days,
        "seaConditions": sea,
        "weatherObserved": weather,
        "waterQuality": water_quality,
    }
