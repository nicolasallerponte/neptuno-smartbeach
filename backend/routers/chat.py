"""Chat API router -- LLM assistant powered by Ollama."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.ollama import chat
from backend.services.orion import get_all_beaches_summary

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    response: str


@router.post("/chat")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """Send a message to the NEPTUNO AI assistant.

    Before calling Ollama, the backend fetches current state of all
    beaches from Orion and injects it as context into the system prompt.
    Conversation history (last 6 exchanges) is forwarded to Ollama for
    multi-turn coherence.
    """
    beach_context = await get_all_beaches_summary()

    history = [{"role": m.role, "content": m.content} for m in req.history] if req.history else None

    response = await chat(
        message=req.message,
        beach_context=beach_context,
        conversation_history=history,
    )

    return ChatResponse(response=response)
