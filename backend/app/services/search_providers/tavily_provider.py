from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.services.search_providers.base import (
    SearchProvider,
    SearchResult,
    fetched_now,
    normalize_source_type,
)


class TavilySearchProvider(SearchProvider):
    provider_name = "tavily"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        safe_limit = max(1, min(int(limit or 5), 10))
        payload = json.dumps(
            {
                "query": query,
                "max_results": safe_limit,
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            }
        ).encode("utf-8")
        request = Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "sk-agent-workbench",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Tavily search failed: HTTP {exc.code} {detail}") from exc

        results: list[SearchResult] = []
        for item in data.get("results", [])[:safe_limit]:
            url = str(item.get("url") or "")
            results.append(
                SearchResult(
                    title=str(item.get("title") or url or "Untitled result"),
                    url=url,
                    snippet=str(item.get("content") or ""),
                    source_type=_classify_url(url),
                    fetched_at=fetched_now(),
                    provider=self.provider_name,
                )
            )
        return results


def _classify_url(url: str) -> str:
    lowered = (url or "").lower()
    if any(
        marker in lowered
        for marker in [
            ".gov",
            ".edu",
            "docs.",
            "developer.",
            "developers.",
            "help.",
            "support.",
            "official",
        ]
    ):
        return "official"
    if any(
        marker in lowered
        for marker in [
            "reddit.com",
            "news.ycombinator.com",
            "twitter.com",
            "x.com",
            "discord.com",
            "medium.com",
        ]
    ):
        return "community"
    if any(
        marker in lowered
        for marker in [
            "techcrunch.com",
            "theverge.com",
            "wired.com",
            "bloomberg.com",
            "reuters.com",
            "wsj.com",
            "forbes.com",
            "36kr.com",
            "huxiu.com",
            "pingwest.com",
        ]
    ):
        return "media"
    return normalize_source_type("unknown")
