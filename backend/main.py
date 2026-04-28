"""
NEPTUNO FastAPI application.

Serves the frontend SPA and provides the REST API for beach data,
historical queries, predictions, alerts, and LLM chat.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("neptuno.backend")

app = FastAPI(
    title="NEPTUNO - Smart Coastal Intelligence Platform",
    description="Real-time monitoring API for beaches in A Coruna, Galicia",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
from backend.routers.alerts import router as alerts_router  # noqa: E402
from backend.routers.beaches import router as beaches_router  # noqa: E402
from backend.routers.chat import router as chat_router  # noqa: E402
from backend.routers.history import router as history_router  # noqa: E402
from backend.routers.predictions import router as predictions_router  # noqa: E402

app.include_router(beaches_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    from backend.services.ollama import check_health as ollama_health

    ollama_ok = await ollama_health()
    return {
        "status": "ok",
        "service": "neptuno-backend",
        "ollama": "connected" if ollama_ok else "disconnected",
    }


# Static frontend files (must be last so API routes take precedence)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info("Serving frontend from %s", frontend_dir)
else:
    logger.warning("Frontend directory not found at %s", frontend_dir)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=True,
    )
