from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SUPPORTED_SOURCE_TYPES = {"official", "app_store", "company_profile", "media"}


def read_source(url: str, source_type: str = "unknown", max_chars: int = 12000) -> dict[str, Any]:
    normalized_type = (source_type or "unknown").strip().lower()
    if normalized_type not in SUPPORTED_SOURCE_TYPES:
        return {
            "status": "unsupported_source_type",
            "url": url,
            "source_type": normalized_type,
            "title": "",
            "clean_text": "",
            "metadata": {"message": "当前阶段暂不支持读取此 source_type。"},
            "extracted_facts": [],
            "candidate_claims": [],
            "source_quotes": [],
        }
    try:
        raw_html = _fetch_url(url)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "status": "read_failed",
            "url": url,
            "source_type": normalized_type,
            "title": "",
            "clean_text": "",
            "metadata": {"error": str(exc)},
            "extracted_facts": [],
            "candidate_claims": [],
            "source_quotes": [],
        }

    parser = _ReadableHTMLParser()
    parser.feed(raw_html)
    title = parser.title or parser.metadata.get("og:title") or parser.metadata.get("twitter:title") or ""
    clean_text = _normalize_text(" ".join(parser.text_parts))[: max(1000, min(max_chars, 50000))]
    metadata = _metadata_for_type(normalized_type, parser.metadata, clean_text)
    extracted_facts = _extract_facts(normalized_type, title, clean_text, metadata)
    source_quotes = _source_quotes(clean_text)
    candidate_claims = [
        {
            "claim": fact,
            "supporting_source": url,
            "confidence": 0.55 if normalized_type in {"official", "app_store"} else 0.45,
        }
        for fact in extracted_facts
    ]
    return {
        "status": "ok",
        "url": url,
        "source_type": normalized_type,
        "title": title,
        "clean_text": clean_text,
        "metadata": metadata,
        "extracted_facts": extracted_facts,
        "candidate_claims": candidate_claims,
        "source_quotes": source_quotes,
    }


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.metadata: dict[str, str] = {}
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True
        if lowered == "meta":
            values = {key.lower(): value or "" for key, value in attrs}
            name = values.get("name") or values.get("property")
            content = values.get("content")
            if name and content:
                self.metadata[name.lower()] = html.unescape(content.strip())

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = _normalize_text(text)
        else:
            self.text_parts.append(text)


def _fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; sk-agent-source-reader/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get("content-type", "")
        charset = "utf-8"
        match = re.search(r"charset=([\w-]+)", content_type, re.I)
        if match:
            charset = match.group(1)
        return response.read().decode(charset, errors="replace")


def _metadata_for_type(source_type: str, metadata: dict[str, str], clean_text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "description": metadata.get("description") or metadata.get("og:description") or "",
        "site_name": metadata.get("og:site_name") or "",
    }
    if source_type == "app_store":
        result.update(
            {
                "rating": _first_match(clean_text, [r"([0-5](?:\.\d)?)\s*(?:star|stars|评分|rating)"]),
                "review_count": _first_match(clean_text, [r"([\d,]+)\s*(?:reviews|ratings|评论|评价)"]),
                "update_date": _first_match(clean_text, [r"(?:updated|更新日期|what'?s new)\s*[:：]?\s*([A-Za-z0-9,\- /年月日]+)"]),
                "app_description": result["description"],
            }
        )
    if source_type == "company_profile":
        result.update(
            {
                "company_description": result["description"],
                "size": _first_match(clean_text, [r"company size\s*[:：]?\s*([^\n.]{2,80})", r"([\d,]+-\d+[,\d]*)\s*employees"]),
                "founded": _first_match(clean_text, [r"founded\s*[:：]?\s*(\d{4})"]),
                "funding": _first_match(clean_text, [r"funding\s*[:：]?\s*([$€£\w., ]{2,80})"]),
            }
        )
    return result


def _extract_facts(source_type: str, title: str, clean_text: str, metadata: dict[str, Any]) -> list[str]:
    facts: list[str] = []
    description = metadata.get("description") or metadata.get("app_description") or metadata.get("company_description")
    if description:
        facts.append(f"{title or source_type} describes: {description[:240]}")
    if source_type == "app_store":
        if metadata.get("rating"):
            facts.append(f"App store page shows rating candidate: {metadata['rating']}")
        if metadata.get("review_count"):
            facts.append(f"App store page shows review count candidate: {metadata['review_count']}")
        if metadata.get("update_date"):
            facts.append(f"App store page shows update date candidate: {metadata['update_date']}")
    if source_type == "company_profile":
        if metadata.get("size"):
            facts.append(f"Company profile shows size candidate: {metadata['size']}")
        if metadata.get("founded"):
            facts.append(f"Company profile shows founded year candidate: {metadata['founded']}")
        if metadata.get("funding"):
            facts.append(f"Company profile shows funding candidate: {metadata['funding']}")
    if not facts and clean_text:
        facts.append(f"{title or source_type} page text is available for manual review.")
    return facts[:8]


def _source_quotes(clean_text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?。！？])\s+", clean_text)
    return [sentence[:500] for sentence in sentences if len(sentence.strip()) >= 40][:5]


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _normalize_text(match.group(1))
    return ""


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()
