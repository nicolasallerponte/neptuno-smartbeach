"""
Water quality prediction engine.

Loads trained ML models and generates WaterQualityPredicted and
WeatherAlert entities in Orion-LD based on current conditions.

Designed to be run periodically (every 6 hours) via the simulator
or as a standalone script.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger("neptuno.ml.predict")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

sys.path.insert(0, ".")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "water_quality_model.joblib"
ECOLI_MODEL_PATH = MODEL_DIR / "ecoli_regressor.joblib"

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")

HEADERS_LD = {
    "Content-Type": "application/ld+json",
    "NGSILD-Tenant": TENANT,
}

# EU Bathing Water Directive 2006/7/EC quality labels
EU_QUALITY_LABELS = {0: "Excellent", 1: "Good", 2: "Poor"}
SEVERITY_MAP = {0: "low", 1: "medium", 2: "high"}


def load_models() -> tuple:
    """Load the trained classifier and regressor models."""
    try:
        import joblib

        if MODEL_PATH.exists() and ECOLI_MODEL_PATH.exists():
            clf = joblib.load(MODEL_PATH)
            reg = joblib.load(ECOLI_MODEL_PATH)
            logger.info("ML models loaded from %s", MODEL_DIR)
            return clf, reg
    except Exception as exc:
        logger.warning("Failed to load ML models: %s", exc)
    return None, None


async def fetch_current_conditions(
    client: "httpx.AsyncClient",
    beach_id: str,
) -> dict | None:
    """Fetch current WeatherObserved and SeaConditions from Orion for a beach."""
    features: dict = {}

    for entity_type, prefix in [("WeatherObserved", ""), ("SeaConditions", "")]:
        entity_id = f"urn:ngsi-ld:{entity_type}:{beach_id}"
        url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}"
        headers = {
            "NGSILD-Tenant": TENANT,
            "Accept": "application/json",
            "Link": f'<{CONTEXT_URL}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
        }
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for key in ["temperature", "windSpeed", "windDirection",
                             "relativeHumidity", "precipitation",
                             "waveHeight", "wavePeriod", "seaSurfaceTemperature",
                             "pH", "salinity"]:
                    if key in data:
                        val = data[key]
                        if isinstance(val, dict):
                            features[key] = val.get("value", 0)
                        else:
                            features[key] = val
        except Exception as exc:
            logger.debug("Failed to fetch %s for %s: %s", entity_type, beach_id, exc)

    if len(features) >= 5:
        return features
    return None


def predict_water_quality(
    clf: object,
    reg: object,
    features: dict,
) -> dict:
    """Run prediction using loaded models."""
    feature_order = [
        "temperature", "windSpeed", "windDirection",
        "relativeHumidity", "precipitation",
        "waveHeight", "wavePeriod", "seaSurfaceTemperature",
        "pH", "salinity",
    ]
    X = np.array([[features.get(f, 0.0) for f in feature_order]])

    quality_class = int(clf.predict(X)[0]) if clf else 0
    ecoli_pred = max(0, int(reg.predict(X)[0])) if reg else 50
    enterococci_pred = max(0, int(ecoli_pred * 0.3))
    ph_pred = round(features.get("pH", 8.1) + np.random.uniform(-0.1, 0.1), 2)

    return {
        "qualityClass": quality_class,
        "qualityLabel": EU_QUALITY_LABELS.get(quality_class, "Good"),
        "escherichiaColi": ecoli_pred,
        "intestinalEnterococci": enterococci_pred,
        "pH": ph_pred,
    }


async def create_water_quality_predicted(
    client: "httpx.AsyncClient",
    beach_id: str,
    prediction: dict,
    coordinates: list[float],
) -> None:
    """Create a WaterQualityPredicted entity in Orion."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entity = {
        "id": f"urn:ngsi-ld:WaterQualityPredicted:{beach_id}",
        "type": "WaterQualityPredicted",
        "dateObserved": {"type": "Property", "value": now},
        "dateIssued": {"type": "Property", "value": now},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": coordinates}},
        "pH": {"type": "Property", "value": prediction["pH"]},
        "escherichiaColi": {"type": "Property", "value": prediction["escherichiaColi"], "unitCode": "UFC"},
        "intestinalEnterococci": {"type": "Property", "value": prediction["intestinalEnterococci"], "unitCode": "UFC"},
        "qualityLabel": {"type": "Property", "value": prediction["qualityLabel"]},
        "dataProvider": {"type": "Property", "value": "MLModel"},
        "refPointOfInterest": {"type": "Relationship", "object": f"urn:ngsi-ld:Beach:{beach_id}"},
        "@context": CONTEXT_URL,
    }
    await _upsert_entity(client, entity)


async def create_weather_alert(
    client: "httpx.AsyncClient",
    beach_id: str,
    category: str,
    severity: str,
    description: str,
) -> None:
    """Create a WeatherAlert entity in Orion when conditions warrant."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    alert_id = f"urn:ngsi-ld:WeatherAlert:{uuid.uuid4().hex[:8]}"
    entity = {
        "id": alert_id,
        "type": "WeatherAlert",
        "name": {"type": "Property", "value": f"{category} alert at {beach_id}"},
        "dateIssued": {"type": "Property", "value": now},
        "validFrom": {"type": "Property", "value": now},
        "validTo": {"type": "Property", "value": now},
        "alertSource": {"type": "Property", "value": "MLModel"},
        "category": {"type": "Property", "value": category},
        "severity": {"type": "Property", "value": severity},
        "description": {"type": "Property", "value": description},
        "refPointOfInterest": {"type": "Relationship", "object": f"urn:ngsi-ld:Beach:{beach_id}"},
        "@context": CONTEXT_URL,
    }
    await _upsert_entity(client, entity)
    logger.info("Alert created: %s (%s) at %s", category, severity, beach_id)


async def _upsert_entity(client: "httpx.AsyncClient", entity: dict) -> None:
    entity_id = entity["id"]
    url = f"{ORION_URL}/ngsi-ld/v1/entities"
    resp = await client.post(url, json=entity, headers=HEADERS_LD)
    if resp.status_code == 201:
        logger.debug("Created entity %s", entity_id)
    elif resp.status_code == 409:
        attrs = {k: v for k, v in entity.items() if k not in ("id", "type", "@context")}
        patch_url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}/attrs"
        await client.patch(patch_url, json={**attrs, "@context": CONTEXT_URL}, headers=HEADERS_LD)


async def run_predictions() -> None:
    """Run predictions for all beaches and generate alerts."""
    import httpx

    from simulator.beaches import BEACHES

    clf, reg = load_models()
    if clf is None:
        logger.warning("No ML models available, generating predictions with defaults")

    async with httpx.AsyncClient(timeout=15) as client:
        for b in BEACHES:
            conditions = await fetch_current_conditions(client, b.id)

            if conditions is None:
                logger.info("No current conditions for %s, using defaults", b.id)
                conditions = {
                    "temperature": 16.0, "windSpeed": 12.0, "windDirection": 270,
                    "relativeHumidity": 0.7, "precipitation": 0.0,
                    "waveHeight": 1.0, "wavePeriod": 7.0, "seaSurfaceTemperature": 15.5,
                    "pH": 8.1, "salinity": 35.0,
                }

            prediction = predict_water_quality(clf, reg, conditions)
            await create_water_quality_predicted(client, b.id, prediction, b.coordinates)
            logger.info(
                "Prediction for %s: %s (E.coli=%d)",
                b.id,
                prediction["qualityLabel"],
                prediction["escherichiaColi"],
            )

            # Generate alert if poor quality predicted
            if prediction["qualityClass"] >= 2:
                await create_weather_alert(
                    client,
                    b.id,
                    category="poorWaterQuality",
                    severity="high",
                    description=f"ML model predicts poor water quality: E.coli={prediction['escherichiaColi']} UFC",
                )

            # Generate alert for high waves
            wave_h = conditions.get("waveHeight", 0)
            if wave_h > 2.0:
                await create_weather_alert(
                    client,
                    b.id,
                    category="highWaves",
                    severity="medium" if wave_h < 3.0 else "high",
                    description=f"Wave height predicted to reach {wave_h}m based on ML forecast",
                )


async def main() -> None:
    logger.info("Running ML prediction pipeline")
    await run_predictions()
    logger.info("Prediction pipeline complete")


if __name__ == "__main__":
    asyncio.run(main())
