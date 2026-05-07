from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings


THINK_RE = re.compile(r"^\s*<think>(.*?)</think>\s*", re.DOTALL)


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class LLMConfigurationError(RuntimeError):
    pass


class MiniMaxClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def config_summary(self) -> dict[str, Any]:
        return {
            "provider": "minimax",
            "api_key_configured": bool(self.settings.minimax_api_key),
            "base_url": self.settings.minimax_base_url,
            "chat_endpoint": self.settings.minimax_chat_endpoint,
            "chat_model": self.settings.minimax_chat_model,
            "temperature": self.settings.minimax_temperature,
        }

    def chat(
        self,
        messages: list[ChatMessage],
        max_completion_tokens: int = 2048,
    ) -> dict[str, Any]:
        if not self.settings.minimax_api_key:
            raise LLMConfigurationError("MINIMAX_API_KEY is not configured")

        payload = {
            "model": self.settings.minimax_chat_model,
            "messages": [self._format_message(message) for message in messages],
            "temperature": self.settings.minimax_temperature,
            "max_completion_tokens": max_completion_tokens,
            "stream": False,
        }
        response = self._post_json(self._chat_url(), payload)
        message = _extract_message(response)
        content = str(message.get("content") or "")
        reasoning = message.get("reasoning_content")
        if reasoning:
            answer = content.strip()
            reasoning_present = True
        else:
            reasoning, answer = _split_reasoning(content)
            reasoning_present = bool(reasoning)
        return {
            "status": "ok",
            "provider": "minimax",
            "model": response.get("model") or self.settings.minimax_chat_model,
            "content": answer,
            "reasoning_present": reasoning_present,
            "usage": response.get("usage"),
            "raw_finish_reason": _extract_finish_reason(response),
        }

    def _format_message(self, message: ChatMessage) -> dict[str, str]:
        return {
            "role": message.role,
            "name": "user" if message.role == "user" else "assistant",
            "content": message.content,
        }

    def _chat_url(self) -> str:
        endpoint = self.settings.minimax_chat_endpoint
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{self.settings.minimax_base_url}{endpoint}"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.minimax_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "sk-agent-workbench",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"MiniMax API request failed: HTTP {exc.code} {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"MiniMax API network request failed: {exc}") from exc


def get_llm_client(settings: Settings) -> MiniMaxClient:
    provider = settings.llm_provider.lower()
    if provider != "minimax":
        raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    return MiniMaxClient(settings)


def _extract_content(response: dict[str, Any]) -> str:
    message = _extract_message(response)
    return str(message.get("content") or "")


def _extract_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") or []
    if not choices:
        return {}
    return choices[0].get("message") or {}


def _extract_finish_reason(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    return choices[0].get("finish_reason")


def _split_reasoning(content: str) -> tuple[str | None, str]:
    match = THINK_RE.match(content)
    if not match:
        return None, content
    reasoning = match.group(1).strip()
    answer = content[match.end() :].strip()
    return reasoning, answer
