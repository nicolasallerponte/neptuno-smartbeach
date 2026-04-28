"""
MeteoGalicia API client.

Fetches real meteorological observations and forecasts from the free
MeteoGalicia API v4. Falls back to realistic simulated values when the
API is unreachable.
"""

from __future__ import annotations

import logging
import math
import os
import random
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("neptuno.meteo")

BASE_URL = "https://servizos.meteogalicia.gal/apiv4"
TIMEOUT = 15.0
_API_KEY = os.getenv("METEOGALICIA_API_KEY", "").strip()


def _extra_params() -> dict[str, str]:
    """Return API key params when a key is configured."""
    return {"API_KEY": _API_KEY} if _API_KEY else {}


async def fetch_observation(
    station_id: int,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Fetch the latest observation from a MeteoGalicia station.

    Returns a dict with keys: temperature, windSpeed, windDirection,
    relativeHumidity, precipitation. Returns None on failure.
    """
    url = f"{BASE_URL}/observacion/ultimosValoresEstacion"
    params: dict[str, Any] = {"idEst": station_id, **_extra_params()}
    try:
        http = client or httpx.AsyncClient(timeout=TIMEOUT)
        resp = await http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not client:
            await http.aclose()

        readings = _parse_observation(data)
        if readings:
            logger.info(
                "REAL observation from MeteoGalicia station %s", station_id
            )
            return readings
    except Exception as exc:
        logger.warning(
            "MeteoGalicia observation unavailable for station %s: %s",
            station_id,
            exc,
        )
    return None


async def fetch_forecast(
    lat: float,
    lon: float,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Fetch numeric weather forecast for a coordinate pair.

    Returns a dict with keys: temperature_min, temperature_max,
    windSpeed, windDirection, precipitationProbability, uVIndexMax.
    Returns None on failure.
    """
    url = f"{BASE_URL}/getNumericForecastInfo"
    params: dict[str, Any] = {
        "coords": f"{lon},{lat}",
        "variables": "temperature,wind,precipitation,sky_state",
        **_extra_params(),
    }
    try:
        http = client or httpx.AsyncClient(timeout=TIMEOUT)
        resp = await http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not client:
            await http.aclose()

        forecast = _parse_forecast(data)
        if forecast:
            logger.info("REAL forecast from MeteoGalicia for (%.4f, %.4f)", lat, lon)
            return forecast
    except Exception as exc:
        logger.warning(
            "MeteoGalicia forecast unavailable for (%.4f, %.4f): %s",
            lat,
            lon,
            exc,
        )
    return None


def _parse_observation(data: Any) -> dict[str, Any] | None:
    """Extract useful fields from MeteoGalicia observation response."""
    try:
        if isinstance(data, dict) and "listaObservacionEstacion" in data:
            entries = data["listaObservacionEstacion"]
            if not entries:
                return None
            latest = entries[0]
            values: dict[str, Any] = {}
            for item in latest.get("listaMedidas", []):
                name = item.get("nomeParametro", "")
                val = item.get("valor")
                if val is None:
                    continue
                if "temperatura" in name.lower():
                    values["temperature"] = round(float(val), 1)
                elif "vento_vel" in name.lower() or "viento" in name.lower():
                    values["windSpeed"] = round(float(val), 1)
                elif "vento_dir" in name.lower():
                    values["windDirection"] = int(float(val))
                elif "humidade" in name.lower() or "humedad" in name.lower():
                    values["relativeHumidity"] = round(float(val) / 100.0, 2)
                elif "precipitacion" in name.lower() or "precip" in name.lower():
                    values["precipitation"] = round(float(val), 1)
            if values.get("temperature") is not None:
                return values
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.debug("Failed to parse MeteoGalicia observation: %s", exc)
    return None


def _parse_forecast(data: Any) -> dict[str, Any] | None:
    """Extract useful fields from MeteoGalicia forecast response."""
    try:
        if isinstance(data, dict) and "features" in data:
            features = data["features"]
            if not features:
                return None
            props = features[0].get("properties", {})
            days = props.get("days", [])
            if not days:
                return None
            day = days[0]
            variables = day.get("variables", {})
            result: dict[str, Any] = {}
            if "temperature" in variables:
                temps = variables["temperature"].get("values", [])
                if temps:
                    t_vals = [v.get("value", 0) for v in temps if v.get("value") is not None]
                    if t_vals:
                        result["temperature_min"] = round(min(t_vals), 1)
                        result["temperature_max"] = round(max(t_vals), 1)
            if "wind" in variables:
                winds = variables["wind"].get("values", [])
                if winds:
                    w_vals = [v.get("moduleValue", 0) for v in winds if v.get("moduleValue") is not None]
                    if w_vals:
                        result["windSpeed"] = round(sum(w_vals) / len(w_vals), 1)
                    d_vals = [v.get("directionValue", 0) for v in winds if v.get("directionValue") is not None]
                    if d_vals:
                        result["windDirection"] = int(sum(d_vals) / len(d_vals))
            result.setdefault("precipitationProbability", 0.1)
            result.setdefault("uVIndexMax", 5)
            return result if result else None
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.debug("Failed to parse MeteoGalicia forecast: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Simulated fallback generators
# ---------------------------------------------------------------------------


def simulated_observation(beach_lat: float) -> dict[str, Any]:
    """Generate a realistic simulated weather observation.

    Temperature varies by latitude and time of day. All values are within
    normal ranges for the Galician Atlantic coast.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour
    base_temp = 15.0 + 4.0 * math.sin(math.pi * (hour - 6) / 12)
    lat_factor = (43.7 - beach_lat) * 2.0
    temp = round(base_temp + lat_factor + random.uniform(-1.5, 1.5), 1)
    wind = round(random.uniform(5.0, 25.0), 1)
    wind_dir = random.choice([180, 225, 270, 315, 0])
    humidity = round(random.uniform(0.55, 0.90), 2)
    precip = round(random.uniform(0.0, 2.0), 1) if random.random() < 0.3 else 0.0
    logger.info("SIMULATED observation generated (lat=%.4f)", beach_lat)
    return {
        "temperature": temp,
        "windSpeed": wind,
        "windDirection": wind_dir,
        "relativeHumidity": humidity,
        "precipitation": precip,
    }


def simulated_forecast() -> dict[str, Any]:
    """Generate a realistic simulated 24h forecast."""
    t_min = round(random.uniform(12.0, 16.0), 1)
    t_max = round(t_min + random.uniform(4.0, 8.0), 1)
    logger.info("SIMULATED forecast generated")
    return {
        "temperature_min": t_min,
        "temperature_max": t_max,
        "windSpeed": round(random.uniform(8.0, 22.0), 1),
        "windDirection": random.choice([180, 225, 270, 315]),
        "precipitationProbability": round(random.uniform(0.0, 0.5), 2),
        "uVIndexMax": random.randint(2, 8),
    }


def simulated_sea_conditions(beach_lat: float) -> dict[str, Any]:
    """Generate realistic simulated sea condition readings."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    swell_factor = 1.0 + 0.3 * math.sin(math.pi * hour / 12)
    wave_h = round(random.uniform(0.3, 2.5) * swell_factor, 2)
    wave_p = round(random.uniform(4.0, 12.0), 1)
    sst = round(14.0 + 3.0 * math.sin(math.pi * (hour - 4) / 12) + random.uniform(-0.5, 0.5), 1)
    logger.info("SIMULATED sea conditions generated (lat=%.4f)", beach_lat)
    return {
        "waveHeight": wave_h,
        "wavePeriod": wave_p,
        "waveLevel": min(5, max(1, int(wave_h / 0.5))),
        "seaSurfaceTemperature": sst,
        "pH": round(random.uniform(7.9, 8.3), 2),
        "salinity": round(random.uniform(34.0, 36.0), 1),
        "windSpeed": round(random.uniform(5.0, 25.0), 1),
        "windDirection": random.choice([180, 225, 270, 315, 0]),
    }


def simulated_water_quality() -> dict[str, Any]:
    """Generate realistic simulated water quality readings."""
    logger.info("SIMULATED water quality generated")
    return {
        "temperature": round(random.uniform(14.0, 19.0), 1),
        "pH": round(random.uniform(7.8, 8.4), 2),
        "conductivity": round(random.uniform(40.0, 55.0), 1),
        "turbidity": round(random.uniform(0.5, 5.0), 1),
        "dissolvedOxygen": round(random.uniform(7.0, 10.0), 1),
        "escherichiaColi": random.randint(10, 200),
        "intestinalEnterococci": random.randint(5, 80),
    }
