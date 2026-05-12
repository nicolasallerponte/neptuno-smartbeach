"""
Windy Webcams integration for NEPTUNO.

Provides snapshot URLs and webcam metadata for beaches with camera coverage.
Supports two source types:
  - Windy (cam_id): imgproxy.windy.com snapshots, 640×480 or 800×450
  - Direct URL: publicly accessible JPEG endpoints from Spanish public sources

Coverage:
  A Coruña   — Windy cameras (Riazor: panoramic bay, Orzán: beach level)
  Ares area  — CAA Mouço (Ría de Ares, updates every 10 min)
  Razo       — PlayaWebcams direct JPEG
  Costa Morte— G24/CRTVG public broadcaster (Fisterra camera)
  Ares/Ferrol— Windy Ares camera
"""

from __future__ import annotations

import os

WINDY_API_KEY = os.getenv("WINDY_API_KEY", "")

# Mapping beach_id → webcam source.
# "cam_id" → Windy imgproxy snapshot (requires cam_id known from API)
# "url"    → direct public JPEG endpoint (no authentication)
WEBCAM_MAP: dict[str, dict] = {
    # --- Windy cameras A Coruña ---
    # cam 1280757387: panoramic bay/harbor view from above → Riazor overview
    # cam 1668786166: beach-level view, shows actual sand and water → Orzán
    "Riazor": {"cam_id": 1280757387, "title": "A Coruña · Bahía"},
    "Orzan":  {"cam_id": 1668786166, "title": "Playa de Orzán"},

    # --- Windy camera Ares area ---
    "Doninos": {"cam_id": 1683292037, "title": "Ares · Ría de Ares"},

    # --- G24/CRTVG — Televisión de Galicia, JPEG público sin autenticación ---
    # fisterra.jpg cubre el litoral de la Costa da Morte (Cabo Fisterra)
    "Laxe":    {
        "url": "https://www.g24.gal/prog24/ARQUIVO/CAMARAS_WEB/fisterra.jpg",
        "title": "Costa da Morte · CRTVG",
        "player_url": "https://www.g24.gal",
    },
    "Carnota": {
        "url": "https://www.g24.gal/prog24/ARQUIVO/CAMARAS_WEB/fisterra.jpg",
        "title": "Costa da Morte · CRTVG",
        "player_url": "https://www.g24.gal",
    },

    # --- PlayaWebcams — JPEG directo para Razo ---
    "Razo": {
        "url": "https://www.playawebcams.com/andy/tiempo-razo-coruna.jpg",
        "title": "Razo · PlayaWebcams",
        "player_url": "https://www.playawebcams.com",
    },

    # --- CAA Mouço — asociación náutica Ares, actualiza cada 10 min ---
    "Mino": {
        "url": "https://www.caamouco.net/webcam2/Video1000M.jpg",
        "title": "Ría de Ares · Caamouco",
        "player_url": "https://www.caamouco.net/portal2/webcam",
    },
    "Cabanas": {
        "url": "https://www.caamouco.net/webcam2/Video1000M.jpg",
        "title": "Ría de Ares · Caamouco",
        "player_url": "https://www.caamouco.net/portal2/webcam",
    },
}


def get_webcam(beach_id: str) -> dict | None:
    """Return webcam info dict for a beach, or None if no camera available."""
    cam = WEBCAM_MAP.get(beach_id)
    if not cam:
        return None

    if "cam_id" in cam:
        snap_url = f"https://imgproxy.windy.com/_/full/plain/current/{cam['cam_id']}/original.jpg"
        player_url = f"https://windy.com/webcams/{cam['cam_id']}"
        provider = "Windy"
    else:
        snap_url = cam["url"]
        player_url = cam.get("player_url", snap_url)
        # Extract domain as provider label
        try:
            provider = player_url.split("/")[2].replace("www.", "")
        except IndexError:
            provider = "Direct"

    return {
        "available": True,
        "title": cam["title"],
        "snapshot_url": snap_url,
        "player_url": player_url,
        "provider": provider,
    }
