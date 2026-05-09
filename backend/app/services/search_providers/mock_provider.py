from __future__ import annotations

from urllib.parse import quote

from app.services.source_classifier import classify_source
from app.services.search_providers.base import SearchProvider, SearchResult, fetched_now


class MockSearchProvider(SearchProvider):
    provider_name = "mock"

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        safe_limit = max(1, min(int(limit or 5), 10))
        templates = [
            ("official", "Official source", "https://example.com/official"),
            ("media", "Media report", "https://example.com/media"),
            ("community", "Community discussion", "https://example.com/community"),
            ("unknown", "Unclassified page", "https://example.com/unknown"),
            ("media", "Background article", "https://example.com/background"),
        ]
        results: list[SearchResult] = []
        for index, (source_type, title, base_url) in enumerate(templates[:safe_limit], start=1):
            url = f"{base_url}?q={quote(query)}&n={index}"
            classification = classify_source(url=url, query=query, title=title)
            results.append(
                SearchResult(
                    title=f"{title}: {query}",
                    url=url,
                    snippet=f"Mock search result for '{query}'. Treat as candidate evidence only.",
                    source_type=source_type if source_type != "unknown" else classification.source_type,
                    source_reason=classification.source_reason if source_type == "unknown" else _reason_for_mock(source_type),
                    fetched_at=fetched_now(),
                    provider=self.provider_name,
                )
            )
        return results


def _reason_for_mock(source_type: str) -> str:
    return {
        "official": "domain matches product official site",
        "media": "media report",
        "community": "community discussion",
    }.get(source_type, "unclassified source")
