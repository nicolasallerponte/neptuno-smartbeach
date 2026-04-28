"""
Orion-LD service client.

Provides async methods to query the Orion-LD Context Broker for
current entity state. Used by the FastAPI backend routers.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("neptuno.services.orion")

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")
TIMEOUT = 10.0


def _headers(accept: str = "application/json") -> dict[str, str]:
    return {
        "Accept": accept,
        "NGSILD-Tenant": TENANT,
        "Link": f'<{CONTEXT_URL}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
    }


async def get_entity(entity_id: str) -> dict[str, Any] | None:
    """Fetch a single entity by ID from Orion-LD."""
    url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, headers=_headers())
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Entity %s not found: %s", entity_id, resp.status_code)
        return None


async def query_entities(
    entity_type: str,
    limit: int = 100,
    attrs: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    """Query entities by type from Orion-LD."""
    url = f"{ORION_URL}/ngsi-ld/v1/entities"
    params: dict[str, Any] = {"type": entity_type, "limit": limit}
    if attrs:
        params["attrs"] = attrs
    if q:
        params["q"] = q

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Query for %s returned %s", entity_type, resp.status_code)
        return []


async def get_all_beaches() -> list[dict[str, Any]]:
    """Fetch all Beach entities with current conditions merged."""
    beaches = await query_entities("Beach")
    result = []

    for beach in beaches:
        beach_id = beach.get("id", "").split(":")[-1]
        enriched = dict(beach)

        # Merge current SeaConditions
        sea = await get_entity(f"urn:ngsi-ld:SeaConditions:{beach_id}")
        if sea:
            enriched["currentSeaConditions"] = _extract_values(sea)

        # Merge current WeatherObserved
        weather = await get_entity(f"urn:ngsi-ld:WeatherObserved:{beach_id}")
        if weather:
            enriched["currentWeather"] = _extract_values(weather)

        # Merge current WaterQualityObserved
        wq = await get_entity(f"urn:ngsi-ld:WaterQualityObserved:{beach_id}")
        if wq:
            enriched["currentWaterQuality"] = _extract_values(wq)

        # Merge forecast
        forecast = await get_entity(f"urn:ngsi-ld:WeatherForecast:{beach_id}")
        if forecast:
            enriched["forecast"] = _extract_values(forecast)

        result.append(enriched)

    return result


async def get_beach_detail(beach_id: str) -> dict[str, Any] | None:
    """Fetch full detail for a single beach including all related entities."""
    beach = await get_entity(f"urn:ngsi-ld:Beach:{beach_id}")
    if not beach:
        return None

    detail = dict(beach)
    detail["currentSeaConditions"] = _extract_values(
        await get_entity(f"urn:ngsi-ld:SeaConditions:{beach_id}") or {}
    )
    detail["currentWeather"] = _extract_values(
        await get_entity(f"urn:ngsi-ld:WeatherObserved:{beach_id}") or {}
    )
    detail["currentWaterQuality"] = _extract_values(
        await get_entity(f"urn:ngsi-ld:WaterQualityObserved:{beach_id}") or {}
    )
    detail["forecast"] = _extract_values(
        await get_entity(f"urn:ngsi-ld:WeatherForecast:{beach_id}") or {}
    )
    detail["prediction"] = _extract_values(
        await get_entity(f"urn:ngsi-ld:WaterQualityPredicted:{beach_id}") or {}
    )

    # Devices
    devices = []
    for prefix in ["boya", "meteo", "sensor-agua"]:
        dev = await get_entity(f"urn:ngsi-ld:Device:{prefix}-{beach_id}")
        if dev:
            devices.append(_extract_values(dev))
    detail["devices"] = devices

    return detail


async def get_alerts() -> list[dict[str, Any]]:
    """Fetch all active WeatherAlert entities."""
    alerts = await query_entities("WeatherAlert")
    return [_extract_values(a) for a in alerts]


async def get_all_beaches_summary() -> str:
    """Build a text summary of all beaches for LLM context injection."""
    beaches = await get_all_beaches()
    lines = []
    for b in beaches:
        name = _val(b, "name", "Unknown")
        beach_id = b.get("id", "")
        sea = b.get("currentSeaConditions", {})
        weather = b.get("currentWeather", {})
        wq = b.get("currentWaterQuality", {})

        line = (
            f"- {name} ({beach_id}): "
            f"Temp={weather.get('temperature', 'N/A')}C, "
            f"Wind={weather.get('windSpeed', 'N/A')}km/h, "
            f"Waves={sea.get('waveHeight', 'N/A')}m, "
            f"SST={sea.get('seaSurfaceTemperature', 'N/A')}C, "
            f"E.coli={wq.get('escherichiaColi', 'N/A')} UFC, "
            f"Occupation={_val(b, 'occupationRate', 'N/A')}"
        )
        lines.append(line)
    return "\n".join(lines)


def _extract_values(entity: dict[str, Any]) -> dict[str, Any]:
    """Flatten NGSI-LD Property/Relationship wrapper to plain values."""
    result: dict[str, Any] = {}
    for key, val in entity.items():
        if key.startswith("@") or key in ("type",):
            result[key] = val
            continue
        if key == "id":
            result["id"] = val
            continue
        if isinstance(val, dict):
            if val.get("type") == "Property":
                result[key] = val.get("value")
            elif val.get("type") == "GeoProperty":
                result[key] = val.get("value")
            elif val.get("type") == "Relationship":
                result[key] = val.get("object")
            else:
                result[key] = val.get("value", val)
        else:
            result[key] = val
    return result


def _val(entity: dict, key: str, default: Any = None) -> Any:
    """Extract a property value from an entity dict."""
    v = entity.get(key)
    if isinstance(v, dict):
        return v.get("value", default)
    return v if v is not None else default
