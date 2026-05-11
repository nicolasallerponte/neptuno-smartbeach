"""
Ollama LLM service client.

Provides the chat completion interface for the NEPTUNO beach assistant.
Injects real-time beach context from Orion-LD into the system prompt
before sending to Ollama.
"""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncGenerator

import httpx

logger = logging.getLogger("neptuno.services.ollama")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
TIMEOUT = 120.0

SYSTEM_PROMPT_TEMPLATE = """You are NEPTUNO, an intelligent coastal assistant for the beaches of A Coruna, Galicia, Spain. You help beachgoers, surfers, and tourists with real-time information about beach conditions, weather, water quality, and safety. You communicate in the user's language (Spanish, Galician, or English).

CURRENT BEACH CONDITIONS (live data from sensors):
{beach_context}

GUIDELINES:
- Be friendly, helpful, and concise
- Reference specific real-time data when answering questions
- Warn about dangerous conditions (high waves, poor water quality, UV)
- Suggest the best beaches based on current conditions for activities like swimming, surfing, or walking
- If asked about a specific beach, provide detailed current conditions
- Convert units as needed (Celsius for temperature, km/h for wind, meters for waves)
- Include relevant safety tips when conditions warrant it
"""


async def chat(
    message: str,
    beach_context: str = "",
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """Send a chat message to Ollama with injected beach context.

    Args:
        message: The user's message
        beach_context: Current beach conditions summary from Orion
        conversation_history: Previous messages for multi-turn context

    Returns:
        The assistant's response text
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        beach_context=beach_context if beach_context else "No sensor data currently available."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history[-6:])

    messages.append({"role": "user", "content": message})

    url = f"{OLLAMA_URL}/api/chat"
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 512,
            "top_p": 0.9,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("message", {}).get("content", "")
            logger.info("Ollama response received (%d chars)", len(response_text))
            return response_text
    except httpx.ConnectError:
        logger.error("Ollama is not reachable at %s", OLLAMA_URL)
        return "I apologize, but the AI assistant is currently offline. Please check that Ollama is running at " + OLLAMA_URL
    except Exception as exc:
        logger.error("Ollama request failed: %s", exc)
        return f"I encountered an error processing your request. Please try again. ({exc})"


async def chat_stream(
    message: str,
    beach_context: str = "",
    conversation_history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a chat response from Ollama token by token."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        beach_context=beach_context if beach_context else "No sensor data currently available."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": message})

    url = f"{OLLAMA_URL}/api/chat"
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": 512,
            "top_p": 0.9,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        import json

                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield "AI assistant is currently offline."
    except Exception as exc:
        yield f"Error: {exc}"


async def check_health() -> bool:
    """Check if Ollama is reachable and the model is available."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                available = [m.get("name", "") for m in models]
                model_available = any(OLLAMA_MODEL in name for name in available)
                if model_available:
                    logger.info("Ollama healthy, model %s available", OLLAMA_MODEL)
                else:
                    logger.warning("Ollama healthy but model %s not found (available: %s)", OLLAMA_MODEL, available)
                return model_available
    except Exception:
        pass
    return False
