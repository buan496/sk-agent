from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from app.db import ensure_schema, get_connection


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")
QUESTION_SPLIT_RE = re.compile(
    r"(有哪些|是什么|在哪里|在哪|哪里|怎么|如何|多少|几个|谁|吗|呢|？|\?)"
)
STOP_TERMS = {
    "哪些",
    "什么",
    "是什么",
    "在哪",
    "哪里",
    "有哪些",
    "怎么",
    "如何",
    "这个",
    "那个",
}
TERM_ALIASES = {
    "格式": ["format", "template"],
    "案例卡": ["case-card", "case card"],
    "case-card": ["案例卡", "format"],
    "case": ["案例"],
    "card": ["卡"],
    "必须条件": ["必选条件", "必要条件"],
}
CANONICAL_PRIORITY = {
    "README.md": 2.0,
    "ops/执行状态总表.md": 2.0,
    "cases/2026/case-index.md": 1.6,
    "cases/2026/case-cards.md": 1.6,
}


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    file_path: str
    heading: str | None
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    keyword_score: float
    file_priority_score: float
    total_score: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["excerpt"] = _excerpt(self.content)
        return data


class Retriever:
    def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        ensure_schema()
        normalized = query.strip()
        if not normalized:
            return {
                "status": "ok",
                "query": query,
                "mode": "keyword",
                "read_files": [],
                "count": 0,
                "results": [],
            }

        terms = _query_terms(normalized)
        rows = self._candidate_rows(terms, max(limit * 120, 800))
        rows.extend(self._path_candidate_rows(terms, max(limit * 8, 40)))
        rows = _dedupe_rows(rows)
        hits = [
            self._score_row(row, normalized, terms)
            for row in rows
        ]
        hits = [hit for hit in hits if hit.total_score > 0]
        hits.sort(key=lambda hit: hit.total_score, reverse=True)
        selected = _diversify_hits(hits, limit)
        return {
            "status": "ok",
            "query": query,
            "mode": "keyword",
            "read_files": _unique([hit.file_path for hit in selected]),
            "count": len(selected),
            "results": [hit.to_dict() for hit in selected],
        }

    def _candidate_rows(self, terms: list[str], limit: int) -> list[dict[str, Any]]:
        if not terms:
            return []
        where = []
        params: list[Any] = []
        for term in terms[:24]:
            pattern = f"%{term}%"
            where.append("(content ILIKE %s OR heading ILIKE %s OR file_path ILIKE %s)")
            params.extend([pattern, pattern, pattern])
        params.append(limit)
        sql = f"""
            SELECT id, file_path, heading, content, start_line, end_line, chunk_type
            FROM chunks
            WHERE {" OR ".join(where)}
            LIMIT %s;
        """
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def _path_candidate_rows(self, terms: list[str], limit: int) -> list[dict[str, Any]]:
        path_terms = [term for term in terms if len(term) >= 4][:30]
        if not path_terms:
            return []
        where = []
        params: list[Any] = []
        for term in path_terms:
            where.append("file_path ILIKE %s")
            params.append(f"%{term}%")
        params.append(limit)
        sql = f"""
            SELECT id, file_path, heading, content, start_line, end_line, chunk_type
            FROM chunks
            WHERE {" OR ".join(where)}
            ORDER BY file_path ASC, ordinal ASC
            LIMIT %s;
        """
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def _score_row(self, row: dict[str, Any], query: str, terms: list[str]) -> SearchHit:
        content = str(row["content"])
        heading = str(row.get("heading") or "")
        file_path = str(row["file_path"])
        haystack = f"{file_path}\n{heading}\n{content}".lower()
        query_lower = query.lower()

        score = 0.0
        if query_lower and query_lower in haystack:
            score += 8.0
        for term in terms:
            term_lower = term.lower()
            if not term_lower:
                continue
            content_hits = content.lower().count(term_lower)
            heading_hits = heading.lower().count(term_lower)
            path_hits = file_path.lower().count(term_lower)
            score += content_hits * 1.0 + heading_hits * 5.0 + path_hits * 12.0
            if path_hits:
                score += min(len(term), 20) * 1.5
            if heading_hits:
                score += min(len(term), 20) * 0.8

        priority = _file_priority(file_path)
        return SearchHit(
            chunk_id=int(row["id"]),
            file_path=file_path,
            heading=row.get("heading"),
            content=content,
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            chunk_type=str(row["chunk_type"]),
            keyword_score=round(score, 4),
            file_priority_score=priority,
            total_score=round(score + priority, 4),
        )


def _query_terms(query: str) -> list[str]:
    terms: list[str] = [query]
    compact = QUESTION_SPLIT_RE.sub(" ", query)
    for part in re.split(r"\s+", compact):
        if len(part) > 1:
            terms.append(part)
    for token in TOKEN_RE.findall(query):
        if len(token) <= 1 or token in STOP_TERMS:
            continue
        terms.append(token)
        if _is_cjk(token) and len(token) >= 4:
            for size in range(2, min(12, len(token)) + 1):
                for start in range(0, len(token) - size + 1):
                    term = token[start : start + size]
                    if term not in STOP_TERMS:
                        terms.append(term)
    for term in list(terms):
        terms.extend(TERM_ALIASES.get(term, []))
    terms.sort(key=len, reverse=True)
    return _unique(terms)


def _is_cjk(value: str) -> bool:
    return all("\u4e00" <= char <= "\u9fff" for char in value)


def _file_priority(file_path: str) -> float:
    if file_path in CANONICAL_PRIORITY:
        return CANONICAL_PRIORITY[file_path]
    if file_path.startswith("core/"):
        return 1.2
    if file_path.startswith("content/"):
        return 1.0
    if file_path.startswith("cases/"):
        return 0.8
    if file_path.startswith("ops/"):
        return 0.8
    return 0.0


def _excerpt(content: str, max_chars: int = 600) -> str:
    clean = re.sub(r"\s+", " ", content).strip()
    if len(clean) <= max_chars:
        return clean
    return f"{clean[:max_chars].rstrip()}..."


def _diversify_hits(hits: list[SearchHit], limit: int, per_file_limit: int = 2) -> list[SearchHit]:
    selected: list[SearchHit] = []
    counts: dict[str, int] = {}
    for hit in hits:
        if counts.get(hit.file_path, 0) >= per_file_limit:
            continue
        selected.append(hit)
        counts[hit.file_path] = counts.get(hit.file_path, 0) + 1
        if len(selected) >= limit:
            return selected
    for hit in hits:
        if hit in selected:
            continue
        selected.append(hit)
        if len(selected) >= limit:
            break
    return selected


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        row_id = int(row["id"])
        if row_id in seen:
            continue
        seen.add(row_id)
        result.append(row)
    return result


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
