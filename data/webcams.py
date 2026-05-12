"""
Windy Webcams integration for NEPTUNO.

Provides snapshot URLs and webcam metadata for beaches with camera coverage.
Snapshots are publicly accessible JPEG images updated periodically by Windy.

Coverage (discovered via Windy Webcams API v3, radius 10 km):
  - A Coruña urban beaches → Torre de Hércules / Orzán cameras
  - Ares estuary beaches → Praia de Redes / Ares cameras
  - Remaining 10 beaches → no coverage in Windy database
"""

from __future__ import annotations

import os

WINDY_API_KEY = os.getenv("WINDY_API_KEY", "")

# Mapping beach_id → Windy webcam metadata
# cam_id discovered via GET /api/v3/webcams?nearby={lat},{lon},10
WEBCAM_MAP: dict[str, dict] = {
    "Riazor":        {"cam_id": 1668786166, "title": "Torre de Hércules · Orzán · Domus"},
    "Orzan":         {"cam_id": 1280757387, "title": "Orzán Beach · Torre de Hércules"},
    "SantaCristina": {"cam_id": 1280757387, "title": "Orzán Beach · Torre de Hércules"},
    "Bastiagueiro":  {"cam_id": 1280757387, "title": "Orzán Beach · Torre de Hércules"},
    "Sabon":         {"cam_id": 1668786166, "title": "Torre de Hércules · Orzán · Domus"},
    "Mino":          {"cam_id": 1344675159, "title": "Praia de Redes · Ría de Ares"},
    "Cabanas":       {"cam_id": 1344675159, "title": "Praia de Redes · Ría de Ares"},
    "Doninos":       {"cam_id": 1683292037, "title": "Ares · Ría de Ares"},
}


def snapshot_url(cam_id: int) -> str:
    """Return the public Windy snapshot JPEG URL for a camera."""
    return f"https://imgproxy.windy.com/_/preview/plain/current/{cam_id}/original.jpg"


def windy_player_url(cam_id: int) -> str:
    return f"https://windy.com/webcams/{cam_id}"


def get_webcam(beach_id: str) -> dict | None:
    """Return webcam info dict for a beach, or None if no camera available."""
    cam = WEBCAM_MAP.get(beach_id)
    if not cam:
        return None
    return {
        "available": True,
        "cam_id": cam["cam_id"],
        "title": cam["title"],
        "snapshot_url": snapshot_url(cam["cam_id"]),
        "player_url": windy_player_url(cam["cam_id"]),
        "provider": "Windy",
    }
