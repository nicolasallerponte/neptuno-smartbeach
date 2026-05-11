"""
Historical data backfill for NEPTUNO SmartBeach.

Generates 7 days of realistic synthetic data and loads it directly into
CrateDB, bypassing the Orion → QuantumLeap pipeline.

Run once after initial setup (idempotent — deletes previous backfill first):
    uv run python simulator/backfill.py
"""

from __future__ import annotations

import logging
import math
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from simulator.beaches import BEACHES, BeachInfo  # noqa: E402

logger = logging.getLogger("neptuno.backfill")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

CRATE_URL = "http://localhost:4200/_sql"
SCHEMA = "mtsmartbeach"
DAYS = 7
SEA_INTERVAL_MINUTES = 10
WEATHER_INTERVAL_MINUTES = 60
WQ_INTERVAL_MINUTES = 720  # 12h


def _smooth_wave(ts: datetime, start: datetime) -> float:
    """Realistic wave height: slow swell cycles, minimal noise for smooth chart."""
    elapsed_h = (ts - start).total_seconds() / 3600
    # Slow storm swell: 3-day period — main driver of wave height variation
    storm = 0.5 + 0.6 * math.sin(2 * math.pi * elapsed_h / 72 + 0.5)
    # Tidal modulation: 12.4h semi-diurnal tidal period
    tidal = 0.7 + 0.3 * math.sin(2 * math.pi * elapsed_h / 12.4)
    base = max(0.15, storm * tidal)
    # Very small noise — wave height is relatively stable over 10 minutes
    noise = random.gauss(0, 0.03)
    return round(max(0.1, base + noise), 2)


def _smooth_sst(ts: datetime, beach_lat: float) -> float:
    """Sea surface temperature close to real maritime value (~13°C for A Coruña)."""
    hour = ts.hour
    # Small diurnal cycle (water heats slowly), small lat offset
    diurnal = 0.3 * math.sin(math.pi * (hour - 8) / 12)
    lat_offset = (43.7 - beach_lat) * 0.2
    noise = random.gauss(0, 0.08)
    return round(13.0 + diurnal + lat_offset + noise, 1)


def _smooth_temp(ts: datetime, beach_lat: float) -> float:
    """Realistic air temperature with diurnal cycle."""
    hour = ts.hour
    lat_offset = (43.7 - beach_lat) * 2.0
    base = 14.0 + 4.0 * math.sin(math.pi * (hour - 6) / 12)
    noise = random.gauss(0, 0.3)
    return round(base + lat_offset + noise, 1)


def _sea_row(beach: BeachInfo, ts: datetime, start: datetime) -> dict:
    wave_h = _smooth_wave(ts, start)
    sst = _smooth_sst(ts, beach.lat)
    entity_id = f"urn:ngsi-ld:SeaConditions:{beach.id}"
    return {
        "entity_id": entity_id,
        "entity_type": "SeaConditions",
        "time_index": ts.isoformat(),
        "fiware_servicepath": "/",
        "instanceid": entity_id,
        "dateobserved": ts.isoformat(),
        "waveheight": wave_h,
        "waveperiod": round(5.0 + 4.0 * math.sin(2 * math.pi * (ts - start).total_seconds() / 43200) + random.gauss(0, 0.3), 1),
        "wavelevel": min(5, max(1, int(wave_h / 0.5))),
        "seasurfacetemperature": sst,
        "ph": round(8.1 + random.gauss(0, 0.08), 2),
        "salinity": round(35.0 + random.gauss(0, 0.4), 1),
    }


def _weather_row(beach: BeachInfo, ts: datetime) -> dict:
    temp = _smooth_temp(ts, beach.lat)
    wind = round(abs(random.gauss(3.5, 1.5)), 1)
    pressure = round(1013.0 + 5.0 * math.sin(2 * math.pi * ts.hour / 24) + random.gauss(0, 1.5), 1)
    entity_id = f"urn:ngsi-ld:WeatherObserved:{beach.id}"
    return {
        "entity_id": entity_id,
        "entity_type": "WeatherObserved",
        "time_index": ts.isoformat(),
        "fiware_servicepath": "/",
        "instanceid": entity_id,
        "dateobserved": ts.isoformat(),
        "temperature": temp,
        "feelsliketemperature": round(temp - wind * 0.6, 1),
        "windspeed": wind,
        "winddirection": random.choice([180, 225, 270, 315, 0]),
        "relativehumidity": round(0.72 + random.gauss(0, 0.08), 2),
        "precipitation": round(max(0, random.gauss(0, 0.3)), 1) if random.random() < 0.25 else 0.0,
        "uvindexmax": max(0, round(5.0 * max(0, math.sin(math.pi * (ts.hour - 6) / 12)) + random.gauss(0, 0.5))),
        "weathertype": "sunnyDay" if ts.hour in range(8, 18) else "partlyCloudy",
        "atmosphericpressure": pressure,
        "windgust": round(wind * (1.4 + random.uniform(0, 0.6)), 1),
        "temperaturemax": round(temp + random.uniform(1.5, 3.5), 1),
        "temperaturemin": round(temp - random.uniform(1.5, 3.5), 1),
        "dewpoint": round(temp - random.uniform(2.0, 5.0), 1),
    }


def _wq_row(beach: BeachInfo, ts: datetime) -> dict:
    entity_id = f"urn:ngsi-ld:WaterQualityObserved:{beach.id}"
    return {
        "entity_id": entity_id,
        "entity_type": "WaterQualityObserved",
        "time_index": ts.isoformat(),
        "fiware_servicepath": "/",
        "instanceid": entity_id,
        "dateobserved": ts.isoformat(),
        "temperature": _smooth_sst(ts, beach.lat),
        "ph": round(8.1 + random.gauss(0, 0.1), 2),
        "conductivity": round(47.0 + random.gauss(0, 2.0), 1),
        "turbidity": round(max(0.2, random.gauss(1.5, 0.8)), 1),
        "dissolvedoxygen": round(8.5 + random.gauss(0, 0.5), 1),
        "escherichiacoli": max(0, round(random.gauss(60, 35))),
        "intestinalenterococci": max(0, round(random.gauss(25, 15))),
    }


def _exec(stmt: str, client: httpx.Client, args=None) -> dict:
    payload = {"stmt": stmt}
    if args is not None:
        payload["args"] = args
    resp = client.post(CRATE_URL, json=payload, headers={"Content-Type": "application/json"})
    return resp.json()


def _bulk_insert(table: str, rows: list[dict], client: httpx.Client) -> int:
    if not rows:
        return 0
    cols = list(rows[0].keys())
    col_str = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join("?" * len(cols))
    stmt = f'INSERT INTO "{SCHEMA}"."{table}" ({col_str}) VALUES ({placeholders})'
    bulk_args = [[row[c] for c in cols] for row in rows]
    resp = client.post(CRATE_URL,
                       json={"stmt": stmt, "bulk_args": bulk_args},
                       headers={"Content-Type": "application/json"})
    if resp.status_code == 200:
        return sum(r.get("rowcount", 0) for r in resp.json().get("results", []))
    logger.error("Insert failed for %s: %s", table, resp.text[:200])
    return 0


def main() -> None:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(days=DAYS)

    with httpx.Client(timeout=60.0) as client:
        # Clear previous backfill data to avoid duplicates
        logger.info("Clearing previous backfill data...")
        for table in ("etseaconditions", "etweatherobserved", "etwaterqualityobserved"):
            result = _exec(
                f'DELETE FROM "{SCHEMA}"."{table}" WHERE time_index < ?',
                client,
                [now.isoformat()],
            )
            logger.info("  Cleared %s: %s", table, result.get("rowcount", "?"))

        for beach in BEACHES:
            logger.info("Backfilling %s...", beach.id)
            sea_rows, wx_rows, wq_rows = [], [], []

            # Sea conditions every 10 minutes
            t = start
            while t < now:
                sea_rows.append(_sea_row(beach, t, start))
                t += timedelta(minutes=SEA_INTERVAL_MINUTES)

            # Weather every hour
            t = start
            while t < now:
                wx_rows.append(_weather_row(beach, t))
                t += timedelta(minutes=WEATHER_INTERVAL_MINUTES)

            # Water quality every 12 hours
            t = start
            while t < now:
                wq_rows.append(_wq_row(beach, t))
                t += timedelta(minutes=WQ_INTERVAL_MINUTES)

            n_sea = _bulk_insert("etseaconditions", sea_rows, client)
            n_wx = _bulk_insert("etweatherobserved", wx_rows, client)
            n_wq = _bulk_insert("etwaterqualityobserved", wq_rows, client)
            logger.info("  %s: sea=%d wx=%d wq=%d rows", beach.id, n_sea, n_wx, n_wq)

    logger.info("Backfill complete for %d beaches over %d days", len(BEACHES), DAYS)


if __name__ == "__main__":
    main()
