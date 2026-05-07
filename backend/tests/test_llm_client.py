from __future__ import annotations

from app.config import Settings
from app.services.llm_client import ChatMessage, MiniMaxClient, _split_reasoning


class FakeMiniMaxClient(MiniMaxClient):
    def _post_json(self, url, payload):  # type: ignore[no-untyped-def]
        assert url == "https://api.minimax.io/v1/chat/completions"
        assert payload["model"] == "MiniMax-M2.7"
        assert payload["messages"][0]["name"] == "user"
        return {
            "model": "MiniMax-M2.7",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "<think>hidden</think>\n\nanswer",
                    },
                }
            ],
            "usage": {"total_tokens": 10},
        }


def test_minimax_client_chat_extracts_answer_and_hides_reasoning() -> None:
    client = FakeMiniMaxClient(
        Settings(
            minimax_api_key="test-key",
            minimax_base_url="https://api.minimax.io/v1",
            minimax_chat_endpoint="/chat/completions",
            minimax_chat_model="MiniMax-M2.7",
        )
    )

    result = client.chat([ChatMessage(role="user", content="hello")])

    assert result["status"] == "ok"
    assert result["content"] == "answer"
    assert result["reasoning_present"] is True
    assert "reasoning" not in result
    assert result["usage"]["total_tokens"] == 10


def test_split_reasoning_without_think_tag() -> None:
    reasoning, answer = _split_reasoning("direct answer")

    assert reasoning is None
    assert answer == "direct answer"


def test_minimax_client_marks_reasoning_content_field_without_exposing_it() -> None:
    class ReasoningFieldClient(MiniMaxClient):
        def _post_json(self, url, payload):  # type: ignore[no-untyped-def]
            return {
                "choices": [
                    {
                        "message": {
                            "content": "answer",
                            "reasoning_content": "hidden reasoning",
                        }
                    }
                ]
            }

    client = ReasoningFieldClient(Settings(minimax_api_key="test-key"))
    result = client.chat([ChatMessage(role="user", content="hello")])

    assert result["content"] == "answer"
    assert result["reasoning_present"] is True
    assert "hidden reasoning" not in str(result)
