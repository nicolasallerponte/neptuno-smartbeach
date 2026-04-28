"""
CV-based alert generator.

Uses the YOLOv11 detector to analyze beach images and generate
WeatherAlert entities in Orion-LD for crowding conditions.

Can run as a standalone periodic script or be called from the backend.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("neptuno.cv.alerts")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

sys.path.insert(0, ".")

ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
CONTEXT_URL = os.getenv("CONTEXT_URL", "http://context/user-context.jsonld")
TENANT = os.getenv("NGSILD_TENANT", "smartbeach")

HEADERS_LD = {
    "Content-Type": "application/ld+json",
    "NGSILD-Tenant": TENANT,
}


async def process_beach_image(
    beach_id: str,
    image_path: str | None = None,
) -> dict | None:
    """Process a beach image and generate alerts if warranted."""
    from cv.detector import detect_occupancy

    result = detect_occupancy(image_path)

    logger.info(
        "Beach %s: %d people detected, occupation=%s (simulated=%s)",
        beach_id,
        result.person_count,
        result.occupation_rate,
        result.is_simulated,
    )

    # Generate an alert for high or very high occupation
    if result.occupation_rate in ("high", "veryHigh"):
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            await _create_crowd_alert(client, beach_id, result.person_count, result.occupation_rate)

    # Also update the Beach entity occupation rate
    await _update_beach_occupation(beach_id, result.occupation_rate)

    return {
        "beach_id": beach_id,
        "person_count": result.person_count,
        "occupation_rate": result.occupation_rate,
        "detections": len(result.detections),
        "is_simulated": result.is_simulated,
    }


async def _create_crowd_alert(
    client: "httpx.AsyncClient",
    beach_id: str,
    person_count: int,
    occupation_rate: str,
) -> None:
    """Create a crowd alert entity in Orion."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    severity = "medium" if occupation_rate == "high" else "high"
    alert_id = f"urn:ngsi-ld:WeatherAlert:cv-{uuid.uuid4().hex[:8]}"

    entity = {
        "id": alert_id,
        "type": "WeatherAlert",
        "name": {"type": "Property", "value": f"High crowd density at {beach_id}"},
        "dateIssued": {"type": "Property", "value": now},
        "validFrom": {"type": "Property", "value": now},
        "validTo": {"type": "Property", "value": now},
        "alertSource": {"type": "Property", "value": "CVSystem"},
        "category": {"type": "Property", "value": "crowding"},
        "severity": {"type": "Property", "value": severity},
        "description": {
            "type": "Property",
            "value": f"Computer vision detected {person_count} people ({occupation_rate} occupation)",
        },
        "refPointOfInterest": {"type": "Relationship", "object": f"urn:ngsi-ld:Beach:{beach_id}"},
        "@context": CONTEXT_URL,
    }

    url = f"{ORION_URL}/ngsi-ld/v1/entities"
    resp = await client.post(url, json=entity, headers=HEADERS_LD)
    if resp.status_code in (201, 409):
        logger.info("Crowd alert created for %s", beach_id)
    else:
        logger.warning("Failed to create crowd alert for %s: %s", beach_id, resp.status_code)


async def _update_beach_occupation(beach_id: str, occupation_rate: str) -> None:
    """Update the occupationRate attribute on the Beach entity."""
    import httpx

    entity_id = f"urn:ngsi-ld:Beach:{beach_id}"
    url = f"{ORION_URL}/ngsi-ld/v1/entities/{entity_id}/attrs"
    payload = {
        "occupationRate": {"type": "Property", "value": occupation_rate},
        "@context": CONTEXT_URL,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(url, json=payload, headers=HEADERS_LD)
        if resp.status_code in (204, 207):
            logger.debug("Beach %s occupation updated to %s", beach_id, occupation_rate)


async def scan_all_beaches() -> list[dict]:
    """Run occupancy detection for all monitored beaches."""
    from simulator.beaches import BEACHES

    results = []
    for b in BEACHES:
        result = await process_beach_image(b.id)
        if result:
            results.append(result)
    return results


async def main() -> None:
    logger.info("Starting CV beach scanning")
    results = await scan_all_beaches()
    for r in results:
        logger.info("  %s: %d people (%s)", r["beach_id"], r["person_count"], r["occupation_rate"])
    logger.info("CV scanning complete")


if __name__ == "__main__":
    asyncio.run(main())
