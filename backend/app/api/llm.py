from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.services.llm_client import ChatMessage, LLMConfigurationError, get_llm_client

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessageRequest(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageRequest] = Field(..., min_length=1)
    max_completion_tokens: int = Field(default=2048, ge=1, le=20000)


@router.get("/config")
def llm_config(settings: Settings = Depends(get_settings)) -> dict:
    client = get_llm_client(settings)
    return {"status": "ok", **client.config_summary()}


@router.post("/chat")
def llm_chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        client = get_llm_client(settings)
        return client.chat(
            [
                ChatMessage(role=message.role, content=message.content)
                for message in request.messages
            ],
            max_completion_tokens=request.max_completion_tokens,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
