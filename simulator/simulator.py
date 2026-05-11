"""
Main sensor data simulator.

Runs a continuous loop that, for every beach:
  1. Fetches real data from MeteoGalicia / MeteoSIX / maritime prediction
  2. Falls back to realistic simulated values when APIs are unavailable
  3. Sends buoy readings (SeaConditions) through the IoT Agent HTTP endpoint
  4. Sends water quality readings (WaterQualityObserved) through the IoT Agent
  5. Directly updates WeatherObserved and WeatherForecast entities in Orion

Intervals are configurable via .env:
  SEA_CONDITIONS_INTERVAL   = 600  (10 min)
  WEATHER_OBSERVED_INTERVAL = 3600 (1 hour)
  WEATHER_FORECAST_INTERVAL = 21600 (6 hours)
  WATER_QUALITY_INTERVAL    = 43200 (12 hours)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from simulator.beaches import (  # noqa: E402
    BEACHES,
    MARITIME_ZONE_MAP,
    METEOGALICIA_STATION_MAP,
    BeachInfo,
)
from simulator.meteo_fetcher import (  # noqa: E402
    fetch_forecast,
    fetch_maritime_prediction,
    fetch_observation,
    simulated_forecast,
    simulated_observation,
    simulated_sea_conditions,
    simulated_water_quality,
)
from data.fetch_real_data import fetch_puertos_sea_state  # noqa: E402
# send_iot_data kept for potential future IoT Agent use

logger = logging.getLogger("neptuno.simulator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
IOT_HTTP_URL = os.getenv("IOT_AGENT_HTTP_URL", "http://localhost:7896")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")
IOT_API_KEY = os.getenv("IOT_API_KEY", "neptuno-smartbeach-2026")
TIMEOUT = 15.0

SEA_INTERVAL = int(os.getenv("SEA_CONDITIONS_INTERVAL", "600"))
WEATHER_INTERVAL = int(os.getenv("WEATHER_OBSERVED_INTERVAL", "3600"))
FORECAST_INTERVAL = int(os.getenv("WEATHER_FORECAST_INTERVAL", "21600"))
WQ_INTERVAL = int(os.getenv("WATER_QUALITY_INTERVAL", "43200"))

HEADERS_LD = {
    "Content-Type": "application/ld+json",
    "NGSILD-Tenant": TENANT,
}


# ---------------------------------------------------------------------------
# IoT Agent data submission
# ---------------------------------------------------------------------------


async def send_iot_data(
    client: httpx.AsyncClient,
    device_id: str,
    payload: dict,
) -> None:
    """Send a measurement payload to the IoT Agent HTTP endpoint."""
    url = f"{IOT_HTTP_URL}/iot/json"
    params = {"k": IOT_API_KEY, "i": device_id}
    try:
        resp = await client.post(url, json=payload, params=params, headers={"Content-Type": "application/json"})
        if resp.status_code in (200, 201, 204):
            logger.debug("IoT data sent for device %s", device_id)
        else:
            logger.warning("IoT Agent returned %s for device %s: %s", resp.status_code, device_id, resp.text)
    except Exception as exc:
        logger.error("Failed to send IoT data for %s: %s", device_id, exc)


# ---------------------------------------------------------------------------
# Direct Orion updates
# ---------------------------------------------------------------------------


async def upsert_orion_entity(
    client: httpx.AsyncClient,
    entity: dict,
) -> None:
    """Create or update an entity directly in Orion-LD."""
    entity_id = entity["id"]
    url = f"{ORION_URL}/ngsi-ld/v1/entities"
    resp = await client.post(url, json=entity, headers=HEADERS_LD)
    if resp.status_code == 201:
        logger.debug("Created entity %s", entity_id)
    elif resp.status_code == 409:
        attrs = {k: v for k, v in entity.items() if k not in ("id", "type", "@context")}
        patch_url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}/attrs"
        pr = await client.patch(patch_url, json={**attrs, "@context": CONTEXT_URL}, headers=HEADERS_LD)
        if pr.status_code in (204, 207):
            logger.debug("Updated entity %s", entity_id)
        else:
            logger.warning("Failed to update %s: %s", entity_id, pr.status_code)
    else:
        logger.warning("Failed to create %s: %s", entity_id, resp.status_code)


# ---------------------------------------------------------------------------
# Update functions per entity type
# ---------------------------------------------------------------------------


async def update_sea_conditions(
    client: httpx.AsyncClient,
    b: BeachInfo,
    maritime: dict[int, dict],
) -> None:
    """Update SeaConditions for one beach directly in Orion-LD."""
    sea = await fetch_puertos_sea_state(b.lat, b.lon, client)
    if sea is None:
        sea = simulated_sea_conditions(b.lat)

    zone_id = MARITIME_ZONE_MAP.get(b.id)
    zone_data = maritime.get(zone_id, {}) if zone_id else {}

    # Use real maritime water temperature when available
    sst = zone_data.get("waterTemperature") or sea["seaSurfaceTemperature"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entity: dict = {
        "id": f"urn:ngsi-ld:SeaConditions:{b.id}",
        "type": "SeaConditions",
        "dateObserved": {"type": "Property", "value": now},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": b.coordinates}},
        "waveHeight": {"type": "Property", "value": sea["waveHeight"], "unitCode": "MTR"},
        "wavePeriod": {"type": "Property", "value": sea["wavePeriod"], "unitCode": "SEC"},
        "waveLevel": {"type": "Property", "value": sea.get("waveLevel", min(5, max(1, int(sea["waveHeight"] / 0.5))))},
        "seaSurfaceTemperature": {"type": "Property", "value": sst, "unitCode": "CEL"},
        "pH": {"type": "Property", "value": sea["pH"]},
        "salinity": {"type": "Property", "value": sea["salinity"]},
        "refPointOfInterest": {"type": "Relationship", "object": b.urn},
        "refDevice": {"type": "Relationship", "object": b.buoy_urn},
        "@context": CONTEXT_URL,
    }
    if zone_data.get("waveHeightText"):
        entity["waveHeightText"] = {"type": "Property", "value": zone_data["waveHeightText"]}
    if zone_data.get("seaStateDescription"):
        entity["seaStateDescription"] = {"type": "Property", "value": zone_data["seaStateDescription"]}
    if zone_data.get("swellDescription"):
        entity["swellDescription"] = {"type": "Property", "value": zone_data["swellDescription"]}

    await upsert_orion_entity(client, entity)


async def update_weather_observed(
    client: httpx.AsyncClient,
    b: BeachInfo,
    maritime: dict[int, dict],
) -> None:
    """Update WeatherObserved via direct Orion PATCH."""
    station_id = METEOGALICIA_STATION_MAP.get(b.id, 14000)
    obs = await fetch_observation(station_id, client)
    if obs is None:
        obs = simulated_observation(b.lat)
    else:
        # Some stations lack pressure/gust sensors — fill gaps with simulation
        sim = simulated_observation(b.lat)
        for _k in ("atmosphericPressure", "windGust", "temperatureMax", "temperatureMin", "dewPoint"):
            if obs.get(_k) is None:
                obs[_k] = sim[_k]

    # Use maritime UV index when available (real value, not derived from humidity)
    zone_id = MARITIME_ZONE_MAP.get(b.id)
    zone_data = maritime.get(zone_id, {}) if zone_id else {}
    uv = zone_data.get("uvMax") or max(1, min(11, int(8 - obs.get("relativeHumidity", 0.7) * 6)))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    feels_like = round(obs["temperature"] - (obs.get("windSpeed", 3.0) * 0.6), 1)
    wt = "lightRain" if obs.get("precipitation", 0) > 0.5 else "sunnyDay"

    entity: dict = {
        "id": f"urn:ngsi-ld:WeatherObserved:{b.id}",
        "type": "WeatherObserved",
        "dateObserved": {"type": "Property", "value": now},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": b.coordinates}},
        "temperature": {"type": "Property", "value": obs["temperature"], "unitCode": "CEL"},
        "feelsLikeTemperature": {"type": "Property", "value": feels_like, "unitCode": "CEL"},
        "windSpeed": {"type": "Property", "value": obs.get("windSpeed", 3.0), "unitCode": "MTS"},
        "windDirection": {"type": "Property", "value": obs.get("windDirection", 270)},
        "relativeHumidity": {"type": "Property", "value": obs.get("relativeHumidity", 0.7)},
        "precipitation": {"type": "Property", "value": obs.get("precipitation", 0.0), "unitCode": "MMT"},
        "uVIndexMax": {"type": "Property", "value": uv},
        "weatherType": {"type": "Property", "value": wt},
        "visibility": {"type": "Property", "value": "good"},
        "dataProvider": {"type": "Property", "value": "MeteoGalicia"},
        "source": {"type": "Property", "value": "https://servizos.meteogalicia.gal/mgrss"},
        "refPointOfInterest": {"type": "Relationship", "object": b.urn},
        "refDevice": {"type": "Relationship", "object": b.meteo_urn},
        "@context": CONTEXT_URL,
    }

    # Optional enriched fields from observation API
    for field, key in [
        ("atmosphericPressure", "atmosphericPressure"),
        ("windGust", "windGust"),
        ("temperatureMax", "temperatureMax"),
        ("temperatureMin", "temperatureMin"),
        ("dewPoint", "dewPoint"),
    ]:
        val = obs.get(key)
        if val is not None:
            entity[field] = {"type": "Property", "value": val}

    await upsert_orion_entity(client, entity)


async def update_weather_forecast(
    client: httpx.AsyncClient,
    b: BeachInfo,
    maritime: dict[int, dict],
) -> None:
    """Update WeatherForecast via direct Orion PATCH."""
    fc = await fetch_forecast(b.lat, b.lon, client)
    if fc is None:
        fc = simulated_forecast()

    # Enrich with maritime zone temperature range when available
    zone_id = MARITIME_ZONE_MAP.get(b.id)
    zone_data = maritime.get(zone_id, {}) if zone_id else {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    wt = fc.get("weatherType", "sunnyDay" if fc.get("precipitationProbability", 0) < 0.3 else "partlyCloudy")

    entity = {
        "id": f"urn:ngsi-ld:WeatherForecast:{b.id}",
        "type": "WeatherForecast",
        "dateIssued": {"type": "Property", "value": now},
        "validFrom": {"type": "Property", "value": now},
        "validTo": {"type": "Property", "value": now},
        "validity": {"type": "Property", "value": f"{now}/{now}"},
        "temperature": {
            "type": "Property",
            "value": {
                "minimum": fc.get("temperature_min", 14.0),
                "maximum": fc.get("temperature_max", 20.0),
            },
        },
        "feelsLikeTemperature": {
            "type": "Property",
            "value": {
                "minimum": round(fc.get("temperature_min", 14.0) - 1.5, 1),
                "maximum": round(fc.get("temperature_max", 20.0) - 1.5, 1),
            },
        },
        "relativeHumidity": {"type": "Property", "value": 0.70},
        "precipitationProbability": {"type": "Property", "value": fc.get("precipitationProbability", 0.1)},
        "windSpeed": {"type": "Property", "value": fc.get("windSpeed", 4.0), "unitCode": "MTS"},
        "windDirection": {"type": "Property", "value": fc.get("windDirection", 270)},
        "weatherType": {"type": "Property", "value": wt},
        "uVIndexMax": {"type": "Property", "value": zone_data.get("uvMax") or fc.get("uVIndexMax", 5)},
        "dataProvider": {"type": "Property", "value": "MeteoGalicia"},
        "refPointOfInterest": {"type": "Relationship", "object": b.urn},
        "@context": CONTEXT_URL,
    }
    await upsert_orion_entity(client, entity)


async def update_water_quality(client: httpx.AsyncClient, b: BeachInfo) -> None:
    """Update WaterQualityObserved directly in Orion-LD."""
    wq = simulated_water_quality()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entity = {
        "id": f"urn:ngsi-ld:WaterQualityObserved:{b.id}",
        "type": "WaterQualityObserved",
        "dateObserved": {"type": "Property", "value": now},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": b.coordinates}},
        "temperature": {"type": "Property", "value": wq["temperature"], "unitCode": "CEL"},
        "pH": {"type": "Property", "value": wq["pH"]},
        "conductivity": {"type": "Property", "value": wq["conductivity"]},
        "turbidity": {"type": "Property", "value": wq["turbidity"]},
        "dissolvedOxygen": {"type": "Property", "value": wq["dissolvedOxygen"]},
        "escherichiaColi": {"type": "Property", "value": wq["escherichiaColi"]},
        "intestinalEnterococci": {"type": "Property", "value": wq["intestinalEnterococci"]},
        "refPointOfInterest": {"type": "Relationship", "object": b.urn},
        "refDevice": {"type": "Relationship", "object": b.water_sensor_urn},
        "@context": CONTEXT_URL,
    }
    await upsert_orion_entity(client, entity)


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------


async def run_cycle(
    client: httpx.AsyncClient,
    cycle: int,
    last_weather: float,
    last_forecast: float,
    last_wq: float,
    now: float,
    maritime_cache: dict[int, dict],
) -> tuple[float, float, float, dict[int, dict]]:
    """Run a single simulation cycle for all beaches."""
    logger.info("=== Simulation cycle %d ===", cycle)

    new_last_weather = last_weather
    new_last_forecast = last_forecast
    new_last_wq = last_wq
    new_maritime = maritime_cache

    # Refresh maritime data on the same cadence as forecast (every 6h)
    if now - last_forecast >= FORECAST_INTERVAL or cycle == 1:
        new_maritime = await fetch_maritime_prediction(client)

    for b in BEACHES:
        await update_sea_conditions(client, b, new_maritime)

    if now - last_weather >= WEATHER_INTERVAL or cycle == 1:
        for b in BEACHES:
            await update_weather_observed(client, b, new_maritime)
        new_last_weather = now
        logger.info("Weather observations updated (%d beaches)", len(BEACHES))

    if now - last_forecast >= FORECAST_INTERVAL or cycle == 1:
        for b in BEACHES:
            await update_weather_forecast(client, b, new_maritime)
        new_last_forecast = now
        logger.info("Weather forecasts updated (%d beaches)", len(BEACHES))

    if now - last_wq >= WQ_INTERVAL or cycle == 1:
        for b in BEACHES:
            await update_water_quality(client, b)
        new_last_wq = now
        logger.info("Water quality updated (%d beaches)", len(BEACHES))

    logger.info("Cycle %d complete for %d beaches", cycle, len(BEACHES))
    return new_last_weather, new_last_forecast, new_last_wq, new_maritime


async def main() -> None:
    import time

    logger.info("NEPTUNO Simulator starting")
    logger.info("Orion: %s | IoT Agent: %s", ORION_URL, IOT_HTTP_URL)
    logger.info("Intervals: sea=%ds weather=%ds forecast=%ds wq=%ds", SEA_INTERVAL, WEATHER_INTERVAL, FORECAST_INTERVAL, WQ_INTERVAL)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(30):
            try:
                resp = await client.get(f"{ORION_URL}/version")
                if resp.status_code == 200:
                    logger.info("Orion-LD is ready")
                    break
            except httpx.ConnectError:
                pass
            logger.info("Waiting for Orion-LD... (%d/30)", attempt + 1)
            await asyncio.sleep(2)
        else:
            logger.error("Orion-LD not ready after 60s, exiting")
            return

        cycle = 0
        last_weather = last_forecast = last_wq = 0.0
        maritime_cache: dict[int, dict] = {}
        while True:
            cycle += 1
            now = time.monotonic()
            try:
                last_weather, last_forecast, last_wq, maritime_cache = await run_cycle(
                    client, cycle, last_weather, last_forecast, last_wq, now, maritime_cache
                )
            except Exception as exc:
                logger.exception("Error in simulation cycle %d: %s", cycle, exc)
            logger.info("Next sea-conditions cycle in %d seconds", SEA_INTERVAL)
            await asyncio.sleep(SEA_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user")
