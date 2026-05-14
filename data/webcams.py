"""
Camaramar HLS webcam integration for NEPTUNO.

Provides live HLS stream URLs and snapshot images for beach cameras.
Sources:
  - Camaramar standard: wow.camaramar.com/camaramar/{id}.stream/
  - Camaramar VOD:      wow.camaramar.com/VODgrabaciones/…/
  - Windy:              imgproxy.windy.com snapshots (Riazor only, no HLS)

Camaramar streams expose Access-Control-Allow-Origin: * so HLS.js can
load them directly from the browser without a backend proxy.
"""

from __future__ import annotations

_CAM_BASE = "https://wow.camaramar.com/camaramar"
_CAM_PLAYER = "https://www.camaramar.com"

# beach_id → webcam source descriptor.
#   hls_id  : Camaramar standard stream (ID_slug), path under _CAM_BASE
#   hls_url : full custom HLS URL (VOD or non-standard path)
#   cam_id  : Windy camera ID (JPEG snapshot only, no live video)
WEBCAM_MAP: dict[str, dict] = {
    # --- A Coruña city — Windy panoramic only (no Camaramar stream) ---
    "Riazor": {"cam_id": 1280757387, "title": "A Coruña · Bahía"},

    # --- A Coruña city area — Camaramar ---
    "Orzan":          {"hls_id": "62_matadero",       "title": "Playa del Matadero"},

    # --- Oleiros (east ría) ---
    "SantaCristina":  {"hls_id": "51_santacristina",  "title": "Santa Cristina"},
    "Bastiagueiro":   {"hls_id": "17_bastiagueiro",   "title": "Bastiagueiro"},

    # --- Ría de Betanzos / north ---
    "Mino":           {"hls_id": "61_perbes",          "title": "Perbes · cerca de Miño"},
    "Cabanas":        {"hls_id": "54_cabana",          "title": "A Cabana · Sada"},

    # --- Ferrol area ---
    "Doninos":        {"hls_id": "11_doninos",         "title": "Doniños"},

    # --- Northern coast ---
    "Valdovino":      {"hls_id": "8_valdovino",        "title": "Valdoviño"},
    "Pantin":         {"hls_id": "20_pantin",          "title": "Pantín"},

    # --- Arteixo / Costa da Morte north ---
    "Sabon": {
        "hls_url":      "https://wow.camaramar.com/VODgrabaciones/meteo_Langosteira.mp4/playlist.m3u8",
        "snapshot_url": "https://wow.camaramar.com/VODgrabaciones/meteo_Langosteira.mp4/snapshot.jpg",
        "title": "Langosteira · Sabón",
    },
    "Caion":    {"hls_id": "44_caionsurfhouse", "title": "Caión Surf House"},
    "Baldaio":  {"hls_id": "49_baldaio",        "title": "Baldaio"},
    "Razo":     {"hls_id": "5_razo",            "title": "Razo"},
    "Malpica":  {"hls_id": "12_malpica",        "title": "Malpica"},

    # --- Costa da Morte south ---
    "Carnota":  {"hls_id": "33_carnota",        "title": "Carnota"},
    # Laxe, Larino, Barona — no Camaramar stream available
}


def get_webcam(beach_id: str) -> dict | None:
    """Return webcam info dict for a beach, or None if no camera available."""
    cam = WEBCAM_MAP.get(beach_id)
    if not cam:
        return None

    if "cam_id" in cam:
        # Windy — JPEG snapshot only, no HLS
        snap_url = f"https://imgproxy.windy.com/_/full/plain/current/{cam['cam_id']}/original.jpg"
        player_url = f"https://windy.com/webcams/{cam['cam_id']}"
        return {
            "available": True,
            "title": cam["title"],
            "hls_url": None,
            "snapshot_url": snap_url,
            "player_url": player_url,
            "provider": "Windy",
        }

    if "hls_id" in cam:
        # Camaramar standard stream
        hls_id = cam["hls_id"]
        base = f"{_CAM_BASE}/{hls_id}.stream"
        return {
            "available": True,
            "title": cam["title"],
            "hls_url": f"{base}/playlist.m3u8",
            "snapshot_url": f"{base}/snapshot.jpg",
            "player_url": _CAM_PLAYER,
            "provider": "Camaramar",
        }

    # Camaramar VOD or custom URL
    return {
        "available": True,
        "title": cam["title"],
        "hls_url": cam.get("hls_url"),
        "snapshot_url": cam.get("snapshot_url"),
        "player_url": cam.get("player_url", _CAM_PLAYER),
        "provider": "Camaramar",
    }
