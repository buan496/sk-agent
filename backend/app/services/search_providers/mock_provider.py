from __future__ import annotations

from urllib.parse import quote

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
            results.append(
                SearchResult(
                    title=f"{title}: {query}",
                    url=f"{base_url}?q={quote(query)}&n={index}",
                    snippet=f"Mock search result for '{query}'. Treat as candidate evidence only.",
                    source_type=source_type,
                    fetched_at=fetched_now(),
                    provider=self.provider_name,
                )
            )
        return results
