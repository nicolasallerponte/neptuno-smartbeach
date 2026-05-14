"""
MeteoGalicia API client.

Data sources:
  - Observations:  free MeteoGalicia mgrss endpoint (no key needed)
  - Forecasts:     MeteoSIX v5 numerical model (METEOSIX_API_KEY required)
  - Maritime:      free MeteoGalicia maritime prediction (no key needed)
                   → water temperature, wave height, UV, sea-state text

Falls back to realistic simulated values when any API is unreachable.
"""

from __future__ import annotations

import logging
import math
import os
import random
from datetime import date, datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("neptuno.meteo")

OBS_BASE_URL = "https://servizos.meteogalicia.gal/mgrss/observacion"
FORECAST_BASE_URL = "https://servizos.meteogalicia.gal/apiv5"
MARITIME_URL = "https://servizos.meteogalicia.gal/mgrss/predicion/jsonPredMaritima.action"
TIMEOUT = 15.0
_METEOSIX_KEY = os.getenv("METEOSIX_API_KEY", "").strip()

# MeteoSIX sky_state codes → NGSI-LD weatherType
_SKY_STATE_MAP: dict[str, str] = {
    "SUNNY": "sunnyDay",
    "PARTLY_CLOUDY": "partlyCloudy",
    "MOSTLY_CLOUDY": "cloudy",
    "OVERCAST": "overcast",
    "RAIN": "lightRain",
    "HEAVY_RAIN": "heavyRain",
    "DRIZZLE": "lightRain",
    "SNOW": "snow",
    "FOG": "fog",
    "THUNDERSTORM": "thunderstorm",
    "HAIL": "hail",
    "MIST": "fog",
}


def _meteosix_params() -> dict[str, str]:
    return {"API_KEY": _METEOSIX_KEY} if _METEOSIX_KEY else {}


# ---------------------------------------------------------------------------
# Observation (free, no key)
# ---------------------------------------------------------------------------

async def fetch_observation(
    station_id: int,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Fetch today's observation summary from a MeteoGalicia station.

    Returns a dict with keys: temperature, windSpeed, windDirection,
    relativeHumidity, precipitation, atmosphericPressure, windGust,
    temperatureMax, temperatureMin, dewPoint. Returns None on failure.
    """
    today = date.today().strftime("%d/%m/%Y")
    url = f"{OBS_BASE_URL}/datosDiariosEstacionsMeteo.action"
    params: dict[str, Any] = {"idEst": station_id, "dataIni": today, "dataFin": today}
    try:
        http = client or httpx.AsyncClient(timeout=TIMEOUT)
        resp = await http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not client:
            await http.aclose()
        readings = _parse_observation(data)
        if readings:
            logger.info("REAL observation from MeteoGalicia station %s", station_id)
            return readings
    except Exception as exc:
        logger.warning("MeteoGalicia observation unavailable for station %s: %s", station_id, exc)
    return None


def _parse_observation(data: Any) -> dict[str, Any] | None:
    """Parse datosDiariosEstacionsMeteo response."""
    try:
        days = data.get("listDatosDiarios", [])
        if not days:
            return None
        stations = days[0].get("listaEstacions", [])
        if not stations:
            return None
        measures = stations[0].get("listaMedidas", [])
        by_code = {
            m["codigoParametro"]: m.get("valor")
            for m in measures
            # filter None and the MeteoGalicia sentinel value for missing data
            if m.get("valor") is not None and float(m.get("valor", 0)) != -9999
        }

        temp = by_code.get("TA_AVG_1.5m")
        if temp is None:
            return None

        result: dict[str, Any] = {"temperature": round(float(temp), 1)}

        wind = by_code.get("VV_AVG_10m")
        if wind is not None:
            result["windSpeed"] = round(float(wind), 1)

        wind_dir = by_code.get("DVP_MODA_10m") or by_code.get("DV_CONDICION_10m")
        if wind_dir is not None:
            result["windDirection"] = int(float(wind_dir))

        humidity = by_code.get("HR_AVG_1.5m")
        if humidity is not None:
            result["relativeHumidity"] = round(float(humidity) / 100.0, 2)

        precip = by_code.get("PP_SUM_1.5m")
        if precip is not None:
            result["precipitation"] = round(float(precip), 1)

        pressure = by_code.get("PR_AVG_1.5m")
        if pressure is not None:
            result["atmosphericPressure"] = round(float(pressure), 1)

        gust = by_code.get("VV_MAX_10m")
        if gust is not None:
            result["windGust"] = round(float(gust), 1)

        t_max = by_code.get("TA_MAX_1.5m")
        if t_max is not None:
            result["temperatureMax"] = round(float(t_max), 1)

        t_min = by_code.get("TA_MIN_1.5m")
        if t_min is not None:
            result["temperatureMin"] = round(float(t_min), 1)

        dew = by_code.get("TO_AVG_1.5m")
        if dew is not None:
            result["dewPoint"] = round(float(dew), 1)

        return result
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.debug("Failed to parse MeteoGalicia observation: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Forecast / MeteoSIX v5 (requires API key)
# ---------------------------------------------------------------------------

async def fetch_forecast(
    lat: float,
    lon: float,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Fetch numerical forecast from MeteoSIX v5.

    Returns a dict with keys: temperature_min, temperature_max,
    windSpeed, windDirection, precipitationProbability, uVIndexMax,
    weatherType. Returns None on failure.
    """
    url = f"{FORECAST_BASE_URL}/getNumericForecastInfo"
    params: dict[str, Any] = {
        "coords": f"{lon},{lat}",
        "variables": "temperature,wind,precipitation_amount,sky_state",
        **_meteosix_params(),
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
            logger.info("REAL forecast from MeteoSIX for (%.4f, %.4f)", lat, lon)
            return forecast
    except Exception as exc:
        logger.warning("MeteoSIX forecast unavailable for (%.4f, %.4f): %s", lat, lon, exc)
    return None


def _parse_forecast(data: Any) -> dict[str, Any] | None:
    """Parse MeteoSIX v5 GeoJSON forecast response.

    v5 uses a list for variables (each entry has a 'name' key), unlike v4.
    Prefers days[1] (first full future day) for min/max temperature.
    """
    try:
        if not isinstance(data, dict) or "features" not in data:
            return None
        features = data["features"]
        if not features:
            return None
        days = features[0].get("properties", {}).get("days", [])
        if not days:
            return None
        day = days[1] if len(days) > 1 else days[0]
        by_name = {v["name"]: v for v in day.get("variables", []) if "name" in v}
        result: dict[str, Any] = {}

        if "temperature" in by_name:
            t_vals = [
                v["value"] for v in by_name["temperature"].get("values", [])
                if v.get("value") is not None
            ]
            if t_vals:
                result["temperature_min"] = round(min(t_vals), 1)
                result["temperature_max"] = round(max(t_vals), 1)

        if "wind" in by_name:
            winds = by_name["wind"].get("values", [])
            w_vals = [v["moduleValue"] for v in winds if v.get("moduleValue") is not None]
            if w_vals:
                result["windSpeed"] = round(sum(w_vals) / len(w_vals), 1)
            d_vals = [v["directionValue"] for v in winds if v.get("directionValue") is not None]
            if d_vals:
                result["windDirection"] = int(sum(d_vals) / len(d_vals))

        if "precipitation_amount" in by_name:
            p_vals = [
                v["value"] for v in by_name["precipitation_amount"].get("values", [])
                if v.get("value") is not None
            ]
            if p_vals:
                result["precipitationProbability"] = min(1.0, round(sum(p_vals) / 10.0, 2))

        if "sky_state" in by_name:
            sky_vals = by_name["sky_state"].get("values", [])
            if sky_vals:
                most_common = max(
                    set(v["value"] for v in sky_vals if v.get("value")),
                    key=lambda s: sum(1 for v in sky_vals if v.get("value") == s),
                    default=None,
                )
                if most_common:
                    result["weatherType"] = _SKY_STATE_MAP.get(most_common, "partlyCloudy")

        result.setdefault("precipitationProbability", 0.1)
        result.setdefault("uVIndexMax", 5)
        result.setdefault("weatherType", "partlyCloudy")
        return result if result else None
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.debug("Failed to parse MeteoSIX forecast: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Maritime prediction (free, no key) — zones 2, 3, 4 cover A Coruña
# ---------------------------------------------------------------------------

async def fetch_maritime_prediction(
    client: httpx.AsyncClient | None = None,
) -> dict[int, dict[str, Any]]:
    """Fetch maritime zone forecasts from MeteoGalicia.

    Returns a dict keyed by zone_id (int) with fields:
    waterTemperature, uvMax, temperatureMax, temperatureMin,
    waveHeightText, seaStateDescription, swellDescription.
    Empty dict on failure.
    """
    params = {"idZona": -1, "dia": -1, "request_locale": "es"}
    try:
        http = client or httpx.AsyncClient(timeout=TIMEOUT)
        resp = await http.get(MARITIME_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not client:
            await http.aclose()
        result = _parse_maritime(data)
        if result:
            logger.info("REAL maritime prediction loaded (%d zones)", len(result))
        return result
    except Exception as exc:
        logger.warning("MeteoGalicia maritime prediction unavailable: %s", exc)
    return {}


def _parse_maritime(data: Any) -> dict[int, dict[str, Any]]:
    """Parse jsonPredMaritima response into a zone_id → data dict."""
    out: dict[int, dict[str, Any]] = {}
    try:
        days = data.get("listaPredDiaMaritima", [])
        if not days:
            return out
        zones = days[0].get("listaPredZonaMaritima", [])
        for z in zones:
            zone_id = z.get("idZona")
            if zone_id is None:
                continue
            wave_range = z.get("alturaOnda", {})
            wave_text = wave_range.get("tarde") or wave_range.get("manha") or ""
            out[zone_id] = {
                "waterTemperature": z.get("tAuga"),
                "uvMax": z.get("uvMax"),
                "temperatureMax": z.get("tMax"),
                "temperatureMin": z.get("tMin"),
                "waveHeightText": str(wave_text) if wave_text else "",
                "seaStateDescription": z.get("comentMar", ""),
                "swellDescription": z.get("comentMarFondo", ""),
            }
    except (KeyError, IndexError, TypeError) as exc:
        logger.debug("Failed to parse maritime prediction: %s", exc)
    return out


# ---------------------------------------------------------------------------
# Simulated fallback generators
# ---------------------------------------------------------------------------


def simulated_observation(beach_lat: float) -> dict[str, Any]:
    """Realistic simulated weather observation for Galician Atlantic coast."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    base_temp = 15.0 + 4.0 * math.sin(math.pi * (hour - 6) / 12)
    lat_factor = (43.7 - beach_lat) * 2.0
    temp = round(base_temp + lat_factor + random.uniform(-1.5, 1.5), 1)
    wind = round(random.uniform(1.5, 7.0), 1)
    wind_dir = random.choice([180, 225, 270, 315, 0])
    humidity = round(random.uniform(0.55, 0.90), 2)
    precip = round(random.uniform(0.0, 2.0), 1) if random.random() < 0.3 else 0.0
    pressure = round(random.uniform(1005.0, 1025.0), 1)
    gust = round(wind * random.uniform(1.3, 2.0), 1)
    logger.info("SIMULATED observation generated (lat=%.4f)", beach_lat)
    return {
        "temperature": temp,
        "windSpeed": wind,
        "windDirection": wind_dir,
        "relativeHumidity": humidity,
        "precipitation": precip,
        "atmosphericPressure": pressure,
        "windGust": gust,
        "temperatureMax": round(temp + random.uniform(1.0, 3.5), 1),
        "temperatureMin": round(temp - random.uniform(1.0, 3.0), 1),
        "dewPoint": round(temp - random.uniform(2.0, 6.0), 1),
    }


def simulated_forecast() -> dict[str, Any]:
    """Realistic simulated 24h forecast."""
    t_min = round(random.uniform(12.0, 16.0), 1)
    t_max = round(t_min + random.uniform(4.0, 8.0), 1)
    logger.info("SIMULATED forecast generated")
    return {
        "temperature_min": t_min,
        "temperature_max": t_max,
        "windSpeed": round(random.uniform(2.0, 8.0), 1),
        "windDirection": random.choice([180, 225, 270, 315]),
        "precipitationProbability": round(random.uniform(0.0, 0.5), 2),
        "uVIndexMax": random.randint(2, 8),
        "weatherType": random.choice(["sunnyDay", "partlyCloudy", "cloudy"]),
    }


def simulated_sea_conditions(beach_lat: float) -> dict[str, Any]:
    """Realistic simulated sea condition readings."""
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
        "windSpeed": round(random.uniform(1.5, 7.0), 1),
        "windDirection": random.choice([180, 225, 270, 315, 0]),
    }


def _seasonal_water_temp(month: int) -> float:
    """Mean SST for Galician Atlantic coast by month (°C)."""
    # Based on Copernicus/EMODnet climatology for NW Iberian shelf
    sst = [13.0, 12.5, 12.5, 13.5, 15.0, 17.0, 18.5, 19.5, 19.0, 17.5, 15.5, 13.5]
    return sst[month - 1]


def _ecoli_season_range(month: int) -> tuple[int, int]:
    """Typical E. coli range (UFC/100ml) by season for Galician beaches.

    Values are low year-round due to good Atlantic flushing, but peak
    slightly in summer (Jul–Aug) from increased bather load.
    """
    if month in (7, 8):          # peak summer
        return (10, 120)
    elif month in (6, 9):        # shoulder
        return (5, 80)
    else:                        # rest of year (bathing season not active)
        return (2, 40)


def simulated_water_quality() -> dict[str, Any]:
    """Season-aware simulated water quality readings."""
    month = datetime.now(timezone.utc).month
    sst = _seasonal_water_temp(month)
    ecoli_lo, ecoli_hi = _ecoli_season_range(month)
    # Dissolved oxygen is inversely related to temperature
    do = round(random.uniform(7.5, 9.5) - (sst - 15.0) * 0.1, 1)
    logger.info("SIMULATED water quality generated (month=%d)", month)
    return {
        "temperature": round(sst + random.uniform(-0.8, 0.8), 1),
        "pH": round(random.uniform(7.9, 8.3), 2),
        "conductivity": round(random.uniform(40.0, 55.0), 1),
        "turbidity": round(random.uniform(0.3, 3.0), 1),
        "dissolvedOxygen": max(6.0, do),
        "escherichiaColi": random.randint(ecoli_lo, ecoli_hi),
        "intestinalEnterococci": random.randint(max(2, ecoli_lo // 2), max(10, ecoli_hi // 2)),
    }
