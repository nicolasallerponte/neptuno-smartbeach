"""
Orion-LD entity initializer.

Creates all static and semi-static NGSI-LD entities at startup:
  - PointOfInterest (one per beach)
  - Beach (one per beach, linked to PointOfInterest)
  - Device (three per beach: buoy, meteo station, water quality sensor)

Also provisions IoT Agent service groups and devices for simulated
sensor data ingestion.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# Append project root so sibling packages are importable
sys.path.insert(0, ".")

from simulator.beaches import BEACHES, BeachInfo  # noqa: E402

logger = logging.getLogger("neptuno.init")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
IOT_AGENT_URL = os.getenv("IOT_AGENT_NORTH_URL", "http://localhost:4041")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")
TIMEOUT = 15.0
IOT_API_KEY = os.getenv("IOT_API_KEY", "neptuno-smartbeach-2026")


HEADERS_LD = {
    "Content-Type": "application/ld+json",
    "NGSILD-Tenant": TENANT,
}

HEADERS_JSON = {
    "Content-Type": "application/json",
    "fiware-service": TENANT,
    "fiware-servicepath": "/",
}


# ---------------------------------------------------------------------------
# Entity builders
# ---------------------------------------------------------------------------


def build_poi(b: BeachInfo) -> dict:
    return {
        "id": b.poi_urn,
        "type": "PointOfInterest",
        "name": {"type": "Property", "value": b.name},
        "description": {"type": "Property", "value": b.description or f"Beach point of interest in {b.city}"},
        "location": {
            "type": "GeoProperty",
            "value": {"type": "Point", "coordinates": b.coordinates},
        },
        "category": {"type": "Property", "value": ["beach"]},
        "address": {
            "type": "Property",
            "value": {"addressLocality": b.city, "addressRegion": "Galicia"},
        },
        "@context": CONTEXT_URL,
    }


def build_beach(b: BeachInfo) -> dict:
    return {
        "id": b.urn,
        "type": "Beach",
        "name": {"type": "Property", "value": b.name},
        "description": {"type": "Property", "value": b.description or f"Monitored beach in {b.city}"},
        "location": {
            "type": "GeoProperty",
            "value": {"type": "Point", "coordinates": b.coordinates},
        },
        "address": {
            "type": "Property",
            "value": {"addressLocality": b.city, "addressRegion": "Galicia"},
        },
        "length": {"type": "Property", "value": b.length, "unitCode": "MTR"},
        "width": {"type": "Property", "value": b.width, "unitCode": "MTR"},
        "beachType": {"type": "Property", "value": b.beach_type},
        "occupationRate": {"type": "Property", "value": "low"},
        "facilities": {"type": "Property", "value": b.facilities},
        "accessType": {"type": "Property", "value": b.access_type},
        "refPointOfInterest": {"type": "Relationship", "object": b.poi_urn},
        "@context": CONTEXT_URL,
    }


def build_device(
    device_id: str,
    name: str,
    description: str,
    controlled: list[str],
    beach: BeachInfo,
) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": device_id,
        "type": "Device",
        "name": {"type": "Property", "value": name},
        "description": {"type": "Property", "value": description},
        "deviceCategory": {"type": "Property", "value": ["sensor"]},
        "controlledProperty": {"type": "Property", "value": controlled},
        "location": {
            "type": "GeoProperty",
            "value": {"type": "Point", "coordinates": beach.coordinates},
        },
        "controlledAsset": {"type": "Relationship", "object": beach.urn},
        "batteryLevel": {"type": "Property", "value": 0.95},
        "dateLastValueReported": {"type": "Property", "value": now},
        "@context": CONTEXT_URL,
    }


# ---------------------------------------------------------------------------
# Orion upsert
# ---------------------------------------------------------------------------


async def upsert_entity(client: httpx.AsyncClient, entity: dict) -> None:
    """Create or overwrite an entity in Orion-LD."""
    entity_id = entity["id"]
    url = f"{ORION_URL}/ngsi-ld/v1/entities"
    resp = await client.post(url, json=entity, headers=HEADERS_LD)
    if resp.status_code == 201:
        logger.info("Created entity %s", entity_id)
    elif resp.status_code == 409:
        # Entity exists; overwrite attributes
        attrs = {k: v for k, v in entity.items() if k not in ("id", "type", "@context")}
        patch_url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}/attrs"
        patch_headers = {**HEADERS_LD}
        pr = await client.patch(patch_url, json={**attrs, "@context": CONTEXT_URL}, headers=patch_headers)
        if pr.status_code in (204, 207):
            logger.info("Updated entity %s", entity_id)
        else:
            logger.error("Failed to update %s: %s %s", entity_id, pr.status_code, pr.text)
    else:
        logger.error("Failed to create %s: %s %s", entity_id, resp.status_code, resp.text)


# ---------------------------------------------------------------------------
# IoT Agent provisioning
# ---------------------------------------------------------------------------


async def provision_iot_service_group(client: httpx.AsyncClient) -> None:
    """Create an IoT Agent service group for NGSI-LD mode."""
    url = f"{IOT_AGENT_URL}/iot/services"
    payload = {
        "services": [
            {
                "apikey": IOT_API_KEY,
                "cbroker": "http://orion:1026",
                "entity_type": "Device",
                "resource": "/iot/json",
            }
        ]
    }
    resp = await client.post(url, json=payload, headers=HEADERS_JSON)
    if resp.status_code in (200, 201):
        logger.info("IoT Agent service group created")
    elif resp.status_code == 409:
        logger.info("IoT Agent service group already exists")
    else:
        logger.warning("IoT Agent service group creation returned %s: %s", resp.status_code, resp.text)


async def provision_iot_device(
    client: httpx.AsyncClient,
    device_id: str,
    entity_name: str,
    entity_type: str,
    attributes: list[dict],
    static_attrs: list[dict],
) -> None:
    """Provision a single device in the IoT Agent."""
    url = f"{IOT_AGENT_URL}/iot/devices"
    payload = {
        "devices": [
            {
                "device_id": device_id,
                "entity_name": entity_name,
                "entity_type": entity_type,
                "attributes": attributes,
                "static_attributes": static_attrs,
            }
        ]
    }
    resp = await client.post(url, json=payload, headers=HEADERS_JSON)
    if resp.status_code in (200, 201):
        logger.info("IoT device %s provisioned", device_id)
    elif resp.status_code == 409:
        logger.info("IoT device %s already exists", device_id)
    else:
        logger.warning("IoT device %s provision returned %s: %s", device_id, resp.status_code, resp.text)


async def provision_beach_devices(client: httpx.AsyncClient, b: BeachInfo) -> None:
    """Provision buoy and water quality sensor devices for a beach."""
    # Buoy device -> SeaConditions entity
    # Attributes follow the official FIWARE SeaConditions Smart Data Model.
    # windSpeed/windDirection belong to WeatherObserved, not SeaConditions.
    await provision_iot_device(
        client,
        device_id=f"boya-{b.id}",
        entity_name=f"urn:ngsi-ld:SeaConditions:{b.id}",
        entity_type="SeaConditions",
        attributes=[
            {"object_id": "wh", "name": "waveHeight", "type": "Number"},
            {"object_id": "wp", "name": "wavePeriod", "type": "Number"},
            {"object_id": "wl", "name": "waveLevel", "type": "Number"},
            {"object_id": "sst", "name": "seaSurfaceTemperature", "type": "Number"},
            {"object_id": "ph", "name": "pH", "type": "Number"},
            {"object_id": "sal", "name": "salinity", "type": "Number"},
        ],
        static_attrs=[
            {"name": "refPointOfInterest", "type": "Relationship", "value": b.urn},
            {"name": "refDevice", "type": "Relationship", "value": b.buoy_urn},
        ],
    )

    # Water quality sensor -> WaterQualityObserved entity
    await provision_iot_device(
        client,
        device_id=f"sensor-agua-{b.id}",
        entity_name=f"urn:ngsi-ld:WaterQualityObserved:{b.id}",
        entity_type="WaterQualityObserved",
        attributes=[
            {"object_id": "temp", "name": "temperature", "type": "Number"},
            {"object_id": "ph", "name": "pH", "type": "Number"},
            {"object_id": "cond", "name": "conductivity", "type": "Number"},
            {"object_id": "turb", "name": "turbidity", "type": "Number"},
            {"object_id": "do", "name": "dissolvedOxygen", "type": "Number"},
            {"object_id": "ecoli", "name": "escherichiaColi", "type": "Number"},
            {"object_id": "entero", "name": "intestinalEnterococci", "type": "Number"},
        ],
        static_attrs=[
            {"name": "refPointOfInterest", "type": "Relationship", "value": b.urn},
            {"name": "refDevice", "type": "Relationship", "value": b.water_sensor_urn},
        ],
    )


# ---------------------------------------------------------------------------
# Main initialization
# ---------------------------------------------------------------------------


async def wait_for_orion(client: httpx.AsyncClient, retries: int = 30) -> bool:
    """Block until Orion-LD is healthy."""
    for i in range(retries):
        try:
            resp = await client.get(f"{ORION_URL}/version")
            if resp.status_code == 200:
                logger.info("Orion-LD is ready")
                return True
        except httpx.ConnectError:
            pass
        logger.info("Waiting for Orion-LD... (%d/%d)", i + 1, retries)
        await asyncio.sleep(2)
    return False


async def wait_for_iot_agent(client: httpx.AsyncClient, retries: int = 20) -> bool:
    """Block until IoT Agent is healthy."""
    for i in range(retries):
        try:
            resp = await client.get(f"{IOT_AGENT_URL}/iot/about")
            if resp.status_code == 200:
                logger.info("IoT Agent is ready")
                return True
        except httpx.ConnectError:
            pass
        logger.info("Waiting for IoT Agent... (%d/%d)", i + 1, retries)
        await asyncio.sleep(2)
    return False


async def main() -> None:
    logger.info("Starting NEPTUNO Orion-LD initialization")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Wait for services
        if not await wait_for_orion(client):
            logger.error("Orion-LD did not become ready, aborting")
            return

        # Create entities for each beach
        for b in BEACHES:
            # 1. PointOfInterest
            await upsert_entity(client, build_poi(b))

            # 2. Beach
            await upsert_entity(client, build_beach(b))

            # 3. Devices (buoy, meteo station, water sensor)
            await upsert_entity(
                client,
                build_device(
                    b.buoy_urn,
                    f"Virtual buoy {b.id}",
                    f"Virtual IoT buoy simulating sea conditions sensor at {b.name}",
                    ["waveHeight", "wavePeriod", "seaSurfaceTemperature", "pH", "salinity"],
                    b,
                ),
            )
            await upsert_entity(
                client,
                build_device(
                    b.meteo_urn,
                    f"Virtual meteo station {b.id}",
                    f"Virtual meteorological station at {b.name}",
                    ["temperature", "windSpeed", "windDirection", "relativeHumidity", "precipitation"],
                    b,
                ),
            )
            await upsert_entity(
                client,
                build_device(
                    b.water_sensor_urn,
                    f"Virtual water quality sensor {b.id}",
                    f"Virtual water quality monitoring sensor at {b.name}",
                    ["pH", "dissolvedOxygen", "escherichiaColi", "intestinalEnterococci", "turbidity"],
                    b,
                ),
            )

        logger.info("All static entities created (%d beaches x 5 entities)", len(BEACHES))

        # Provision IoT Agent
        if await wait_for_iot_agent(client):
            await provision_iot_service_group(client)
            for b in BEACHES:
                await provision_beach_devices(client, b)
            logger.info("IoT Agent provisioning complete")
        else:
            logger.warning("IoT Agent not ready, skipping device provisioning")

    logger.info("Initialization complete")


if __name__ == "__main__":
    asyncio.run(main())
