from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.services.search_providers.base import SearchProvider
from app.services.search_providers.mock_provider import MockSearchProvider
from app.services.search_providers.tavily_provider import TavilySearchProvider


def search_web(query: str, limit: int = 5, settings: Settings | None = None) -> dict[str, Any]:
    active_settings = settings or get_settings()
    safe_limit = max(1, min(int(limit or 5), 10))
    provider = _provider(active_settings)
    warnings: list[str] = []
    try:
        results = provider.search(query=query.strip(), limit=safe_limit)
    except Exception as exc:
        warnings.append(f"{provider.provider_name} 搜索失败，已回退 mock：{exc}")
        provider = MockSearchProvider()
        results = provider.search(query=query.strip(), limit=safe_limit)
    return {
        "query": query,
        "provider": provider.provider_name,
        "results": [item.to_dict() for item in results],
        "warnings": warnings,
    }


def _provider(settings: Settings) -> SearchProvider:
    provider_name = (settings.web_search_provider or "tavily").strip().lower()
    if settings.tavily_api_key and provider_name != "mock":
        return TavilySearchProvider(settings.tavily_api_key)
    return MockSearchProvider()
