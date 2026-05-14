"""Webcam API router."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from data.webcams import get_webcam

router = APIRouter(tags=["webcams"])


@router.get("/beaches/{beach_id}/webcam")
async def get_beach_webcam(beach_id: str) -> dict:
    """Return webcam info for a beach (hls_url + snapshot_url), if available."""
    info = get_webcam(beach_id)
    if not info:
        return {"available": False}
    return info


@router.get("/beaches/{beach_id}/webcam/snapshot")
async def proxy_webcam_snapshot(beach_id: str):
    """Proxy the webcam snapshot image to avoid browser CORS restrictions."""
    info = get_webcam(beach_id)
    if not info:
        raise HTTPException(status_code=404, detail="No webcam for this beach")

    url = info["snapshot_url"]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Referer": info.get("player_url", url),
    }

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={"Cache-Control": "no-cache"},
    )
