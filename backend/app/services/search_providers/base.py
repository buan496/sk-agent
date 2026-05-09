from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
SOURCE_TYPES = {"official", "app_store", "company_profile", "media", "community", "unknown"}


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source_type: str
    source_reason: str
    fetched_at: str
    provider: str

    def to_dict(self) -> dict:
        return asdict(self)


class SearchProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        raise NotImplementedError


def fetched_now() -> str:
    return datetime.now(tz=SHANGHAI_TZ).isoformat(timespec="seconds")


def normalize_source_type(value: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in SOURCE_TYPES else "unknown"
