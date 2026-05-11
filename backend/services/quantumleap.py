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
    aggr_method: str | None = None,
    aggr_period: str | None = None,
) -> dict[str, Any]:
    """Fetch time series for a single entity from QuantumLeap.

    Args:
        entity_type: NGSI-LD entity type (e.g. "SeaConditions")
        entity_id: Entity ID without the URN prefix
        attrs: Comma-separated attribute names to fetch
        last_n: Number of most recent values to return
        from_date: ISO 8601 start date filter
        to_date: ISO 8601 end date filter
        aggr_method: Aggregation method (avg, max, min, sum)
        aggr_period: Aggregation period in ISO 8601 (e.g. "PT1H")

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
    if aggr_method:
        params["aggrMethod"] = aggr_method
    if aggr_period:
        params["aggrPeriod"] = aggr_period

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


CRATE_URL = os.getenv("CRATE_URL", "http://localhost:4200")


async def get_sea_history_hourly(beach_id: str, days: int = 7) -> dict[str, Any]:
    """Query CrateDB directly for hourly-averaged sea conditions.

    Returns data in QuantumLeap-compatible format with smooth hourly values.
    """
    entity_id = f"urn:ngsi-ld:SeaConditions:{beach_id}"
    import time as _time
    cutoff_ms = int((_time.time() - days * 86400) * 1000)
    # Embed cutoff as literal — CrateDB parameter binding has type issues with ms timestamps
    sql = f"""
        SELECT
            date_trunc('hour', time_index) AS hour,
            avg(waveheight) AS waveheight,
            avg(waveperiod) AS waveperiod,
            avg(seasurfacetemperature) AS sst
        FROM mtsmartbeach.etseaconditions
        WHERE entity_id = ?
          AND time_index >= {cutoff_ms}
          AND waveheight IS NOT NULL
        GROUP BY hour
        ORDER BY hour
    """
    seconds = days * 86400
    url = f"{CRATE_URL}/_sql"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                url,
                json={"stmt": sql, "args": [entity_id, cutoff_ms]},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()
            rows = data.get("rows", [])
            if not rows:
                return {}
            index = [r[0] for r in rows]
            wh = [round(r[1], 2) if r[1] is not None else None for r in rows]
            wp = [round(r[2], 1) if r[2] is not None else None for r in rows]
            sst = [round(r[3], 1) if r[3] is not None else None for r in rows]
            return {
                "index": index,
                "attributes": [
                    {"attrName": "waveHeight", "values": wh},
                    {"attrName": "wavePeriod", "values": wp},
                    {"attrName": "seaSurfaceTemperature", "values": sst},
                ],
            }
    except Exception as exc:
        logger.warning("CrateDB sea history query failed: %s", exc)
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
    Sea conditions sampled every 10 min → 6/h; weather every hour.
    We cap the points to ~168 to keep charts readable (1 pt/hour for 7 days).
    """
    weather_last_n = days * 24
    wq_last_n = max(14, days * 2)

    # Sea conditions: query CrateDB directly with hourly aggregation for smooth charts
    sea = await get_sea_history_hourly(beach_id, days)

    weather = await get_entity_history(
        "WeatherObserved",
        beach_id,
        attrs="temperature,windSpeed,relativeHumidity,precipitation",
        last_n=weather_last_n,
    )

    water_quality = await get_entity_history(
        "WaterQualityObserved",
        beach_id,
        attrs="escherichiaColi,intestinalEnterococci,pH,turbidity,dissolvedOxygen",
        last_n=wq_last_n,
    )

    return {
        "beachId": beach_id,
        "days": days,
        "seaConditions": sea,
        "weatherObserved": weather,
        "waterQuality": water_quality,
    }
