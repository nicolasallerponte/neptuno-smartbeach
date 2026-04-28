"""
QuantumLeap subscription creator.

Creates NGSI-LD subscriptions in Orion-LD so that every update to a
dynamic entity type is forwarded to QuantumLeap for time-series
persistence in CrateDB.

Six subscriptions, one per dynamic entity type:
  - SeaConditions
  - WeatherObserved
  - WeatherForecast
  - WeatherAlert
  - WaterQualityObserved
  - WaterQualityPredicted
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("neptuno.subscriptions")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
QUANTUMLEAP_NOTIFY_URL = os.getenv("QUANTUMLEAP_NOTIFY_URL", "http://quantumleap:8668/v2/notify")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")
TIMEOUT = 15.0

ENTITY_TYPES = [
    "SeaConditions",
    "WeatherObserved",
    "WeatherForecast",
    "WeatherAlert",
    "WaterQualityObserved",
    "WaterQualityPredicted",
]


def build_subscription(entity_type: str) -> dict:
    """Build an NGSI-LD subscription payload for QuantumLeap."""
    return {
        "type": "Subscription",
        "description": f"QuantumLeap subscription for {entity_type}",
        "entities": [{"type": entity_type}],
        "notification": {
            "endpoint": {
                "uri": QUANTUMLEAP_NOTIFY_URL,
                "accept": "application/json",
                "receiverInfo": [
                    {"key": "fiware-service", "value": TENANT},
                    {"key": "fiware-servicepath", "value": "/"},
                ],
            },
        },
        "@context": CONTEXT_URL,
    }


async def wait_for_orion(client: httpx.AsyncClient, retries: int = 30) -> bool:
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


async def create_subscription(client: httpx.AsyncClient, entity_type: str) -> None:
    """Create a single NGSI-LD subscription."""
    url = f"{ORION_URL}/ngsi-ld/v1/subscriptions/"
    headers = {
        "Content-Type": "application/ld+json",
        "NGSILD-Tenant": TENANT,
    }
    payload = build_subscription(entity_type)
    resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 201:
        location = resp.headers.get("Location", "unknown")
        logger.info("Subscription created for %s -> %s", entity_type, location)
    elif resp.status_code == 409:
        logger.info("Subscription for %s already exists", entity_type)
    else:
        logger.error(
            "Failed to create subscription for %s: %s %s",
            entity_type,
            resp.status_code,
            resp.text,
        )


async def list_subscriptions(client: httpx.AsyncClient) -> None:
    """List existing subscriptions for debugging."""
    url = f"{ORION_URL}/ngsi-ld/v1/subscriptions/"
    headers = {"NGSILD-Tenant": TENANT, "Accept": "application/ld+json", "Link": f'<{CONTEXT_URL}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'}
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        subs = resp.json()
        logger.info("Active subscriptions: %d", len(subs))
        for sub in subs:
            desc = sub.get("description", sub.get("id", "?"))
            logger.info("  - %s", desc)


async def main() -> None:
    logger.info("Starting QuantumLeap subscription setup")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if not await wait_for_orion(client):
            logger.error("Orion-LD did not become ready, aborting")
            sys.exit(1)

        for entity_type in ENTITY_TYPES:
            await create_subscription(client, entity_type)

        await list_subscriptions(client)

    logger.info("Subscription setup complete")


if __name__ == "__main__":
    asyncio.run(main())
