from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import Settings
from app.db import ensure_schema, get_connection


NODE_LABELS = {
    "Product",
    "Case",
    "Article",
    "Framework",
    "FailureMode",
    "Theory",
    "File",
    "Decision",
    "Signal",
}
REL_TYPES = {
    "APPEARS_IN",
    "TRIGGERS",
    "USES",
    "REFERENCES",
    "HAS_DECISION",
}
FAILURE_MODE_RE = re.compile(r"\b(FM\d{3})\b", re.IGNORECASE)
CASE_RE = re.compile(r"\b(CASE-[A-Za-z0-9_-]+|\d{3}[A-Z]?)\b")
PRODUCT_FIELD_RE = re.compile(r"(?:product|产品|产品名)\s*[:：]\s*([^\n\r#|，,]+)", re.IGNORECASE)
DECISION_RE = re.compile(r"(?:判为|判断为|decision\s*[:：])\s*([^\n\r#|，,]+)", re.IGNORECASE)
SIGNAL_RE = re.compile(r"(?:signal|信号|触发器|trigger)\s*[:：]\s*([^\n\r#|，,]+)", re.IGNORECASE)
THEORY_RE = re.compile(r"(?:理论|theory)\s*[:：]\s*([^\n\r#|，,]+)", re.IGNORECASE)

FRAMEWORK_TERMS = [
    "诊断空白",
    "MTP",
    "构思招募",
    "项目审问",
    "产品评估",
    "failure_modes",
    "case-card",
    "案例卡",
    "发布 SOP",
]
THEORY_TERMS = [
    "诊断空白",
    "MTP",
    "构思招募法",
    "产品评估决策",
]


@dataclass(frozen=True)
class GraphNode:
    label: str
    id: str
    properties: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GraphRelationship:
    source_label: str
    source_id: str
    rel_type: str
    target_label: str
    target_id: str
    properties: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GraphUnavailableError(RuntimeError):
    pass


class GraphBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rebuild(self) -> dict[str, Any]:
        rows = _load_chunks()
        graph = build_graph(rows)
        with self._driver() as driver:
            try:
                with driver.session() as session:
                    session.run("RETURN 1").consume()
                    _prepare_schema(session)
                    session.run("MATCH (n) DETACH DELETE n").consume()
                    for node in graph["nodes"]:
                        _write_node(session, node)
                    for relationship in graph["relationships"]:
                        _write_relationship(session, relationship)
                    _write_graph_meta(session, source_chunk_count=len(rows))
            except (Neo4jError, ServiceUnavailable) as exc:
                raise GraphUnavailableError(f"Neo4j unavailable: {exc}") from exc

        return {
            "status": "ok",
            "source_chunk_count": len(rows),
            "node_count": len(graph["nodes"]),
            "relationship_count": len(graph["relationships"]),
            "labels": _count_by_label(graph["nodes"]),
            "relationship_types": _count_by_rel_type(graph["relationships"]),
        }

    def status(self) -> dict[str, Any]:
        with self._driver() as driver:
            try:
                with driver.session() as session:
                    node_count = session.run(
                        "MATCH (n) WHERE NOT n:GraphMeta RETURN count(n) AS count"
                    ).single()["count"]
                    relationship_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
                    labels = session.run(
                        """
                        MATCH (n)
                        WHERE NOT n:GraphMeta
                        UNWIND labels(n) AS label
                        RETURN label, count(*) AS count
                        ORDER BY label
                        """
                    ).data()
                    rel_types = session.run(
                        """
                        MATCH ()-[r]->()
                        RETURN type(r) AS type, count(*) AS count
                        ORDER BY type
                        """
                    ).data()
                    meta = session.run(
                        """
                        MATCH (m:GraphMeta {id: 'latest'})
                        RETURN toString(m.rebuilt_at) AS graph_rebuild_time,
                               m.source_chunk_count AS source_chunk_count
                        """
                    ).single()
            except (Neo4jError, ServiceUnavailable) as exc:
                raise GraphUnavailableError(f"Neo4j unavailable: {exc}") from exc
        return {
            "status": "ok",
            "node_count": node_count,
            "relationship_count": relationship_count,
            "labels": labels,
            "relationship_types": rel_types,
            "latest_index_run": _latest_index_run(),
            "graph_rebuild_time": meta["graph_rebuild_time"] if meta else None,
            "source_chunk_count": meta["source_chunk_count"] if meta else None,
        }

    def cases_for_failure_mode(self, code: str) -> dict[str, Any]:
        normalized = code.strip().upper()
        return self._query(
            """
            MATCH (c:Case)-[r:TRIGGERS]->(fm:FailureMode {id: $code})
            OPTIONAL MATCH (c)-[:APPEARS_IN]->(f:File)
            RETURN c.id AS case_id, c.title AS title, f.path AS file_path, r.line AS line
            ORDER BY file_path, case_id
            """,
            {"code": normalized},
            "failure_mode_cases",
        )

    def articles_for_framework(self, framework: str) -> dict[str, Any]:
        name = framework.strip()
        return self._query(
            """
            MATCH (fw:Framework)
            WHERE fw.name CONTAINS $name OR fw.id CONTAINS $name
            MATCH (a:Article)-[r:REFERENCES|USES]->(fw)
            OPTIONAL MATCH (a)-[:APPEARS_IN]->(f:File)
            RETURN DISTINCT a.id AS article_id, a.title AS title, f.path AS file_path, fw.name AS framework
            ORDER BY file_path, article_id
            """,
            {"name": name},
            "framework_articles",
        )

    def tool_products(self) -> dict[str, Any]:
        return self._query(
            """
            MATCH (p:Product)-[:HAS_DECISION]->(d:Decision)
            WHERE d.value CONTAINS '工具'
            OPTIONAL MATCH (p)-[:APPEARS_IN]->(f:File)
            RETURN DISTINCT p.id AS product_id, p.name AS product, d.value AS decision, f.path AS file_path
            ORDER BY product
            """,
            {},
            "tool_products",
        )

    def reused_theories(self, min_cases: int = 2) -> dict[str, Any]:
        return self._query(
            """
            MATCH (c:Case)-[:REFERENCES|USES]->(t:Theory)
            WITH t, collect(DISTINCT c.id) AS cases
            WHERE size(cases) >= $min_cases
            RETURN t.id AS theory_id, t.name AS theory, cases, size(cases) AS case_count
            ORDER BY case_count DESC, theory
            """,
            {"min_cases": min_cases},
            "reused_theories",
        )

    def _query(self, cypher: str, params: dict[str, Any], name: str) -> dict[str, Any]:
        with self._driver() as driver:
            try:
                with driver.session() as session:
                    rows = session.run(cypher, params).data()
            except (Neo4jError, ServiceUnavailable) as exc:
                raise GraphUnavailableError(f"Neo4j unavailable: {exc}") from exc
        return {
            "status": "ok",
            "query": name,
            "count": len(rows),
            "results": rows,
        }

    def _driver(self):
        return GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )


def build_graph(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    nodes: dict[tuple[str, str], GraphNode] = {}
    relationships: dict[tuple[str, str, str, str, str], GraphRelationship] = {}

    for row in rows:
        file_path = str(row.get("file_path") or "")
        heading = str(row.get("heading") or "")
        content = str(row.get("content") or "")
        text = f"{heading}\n{content}"
        line = int(row.get("start_line") or 0)

        file_node = GraphNode(
            label="File",
            id=file_path,
            properties={
                "id": file_path,
                "path": file_path,
                "kind": _file_kind(file_path),
            },
        )
        _add_node(nodes, file_node)

        article = _article_node(file_path, heading)
        if article:
            _add_node(nodes, article)
            _add_rel(relationships, article, "APPEARS_IN", file_node, {"line": line})

        case = _case_node(file_path, heading, text)
        if case:
            _add_node(nodes, case)
            _add_rel(relationships, case, "APPEARS_IN", file_node, {"line": line})
            if article:
                _add_rel(relationships, article, "REFERENCES", case, {"line": line})

        product = _product_node(file_path, heading, text)
        if product:
            _add_node(nodes, product)
            _add_rel(relationships, product, "APPEARS_IN", file_node, {"line": line})
            if article:
                _add_rel(relationships, article, "REFERENCES", product, {"line": line})
            if case:
                _add_rel(relationships, case, "REFERENCES", product, {"line": line})

        for code in sorted({match.group(1).upper() for match in FAILURE_MODE_RE.finditer(text)}):
            failure_mode = GraphNode(
                label="FailureMode",
                id=code,
                properties={"id": code, "code": code},
            )
            _add_node(nodes, failure_mode)
            _add_rel(relationships, failure_mode, "APPEARS_IN", file_node, {"line": line})
            if case:
                _add_rel(relationships, case, "TRIGGERS", failure_mode, {"line": line})
            if article:
                _add_rel(relationships, article, "REFERENCES", failure_mode, {"line": line})

        for name in _frameworks_in_text(text):
            framework = GraphNode(
                label="Framework",
                id=name,
                properties={"id": name, "name": name},
            )
            _add_node(nodes, framework)
            _add_rel(relationships, framework, "APPEARS_IN", file_node, {"line": line})
            if article:
                _add_rel(relationships, article, "REFERENCES", framework, {"line": line})
            if case:
                _add_rel(relationships, case, "USES", framework, {"line": line})

        for name in _theories_in_text(text):
            theory = GraphNode(
                label="Theory",
                id=name,
                properties={"id": name, "name": name},
            )
            _add_node(nodes, theory)
            _add_rel(relationships, theory, "APPEARS_IN", file_node, {"line": line})
            if article:
                _add_rel(relationships, article, "REFERENCES", theory, {"line": line})
            if case:
                _add_rel(relationships, case, "REFERENCES", theory, {"line": line})

        decision_value = _first_clean_match(DECISION_RE, text)
        if decision_value:
            decision = GraphNode(
                label="Decision",
                id=f"{file_path}#{line}#decision",
                properties={"id": f"{file_path}#{line}#decision", "value": decision_value},
            )
            _add_node(nodes, decision)
            _add_rel(relationships, decision, "APPEARS_IN", file_node, {"line": line})
            if product:
                _add_rel(relationships, product, "HAS_DECISION", decision, {"line": line})

        signal_value = _first_clean_match(SIGNAL_RE, text)
        if signal_value:
            signal = GraphNode(
                label="Signal",
                id=f"{file_path}#{line}#signal",
                properties={"id": f"{file_path}#{line}#signal", "value": signal_value},
            )
            _add_node(nodes, signal)
            _add_rel(relationships, signal, "APPEARS_IN", file_node, {"line": line})
            if product:
                _add_rel(relationships, product, "REFERENCES", signal, {"line": line})

    return {
        "nodes": list(nodes.values()),
        "relationships": list(relationships.values()),
    }


def _load_chunks() -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT file_path, heading, content, start_line, end_line, chunk_type, ordinal
                FROM chunks
                ORDER BY file_path ASC, ordinal ASC;
                """
            )
            return cursor.fetchall()


def _prepare_schema(session) -> None:
    for label in NODE_LABELS:
        session.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE").consume()


def _write_node(session, node: GraphNode) -> None:
    _validate_label(node.label)
    session.run(
        f"MERGE (n:{node.label} {{id: $id}}) SET n += $properties",
        {"id": node.id, "properties": node.properties},
    ).consume()


def _write_relationship(session, relationship: GraphRelationship) -> None:
    _validate_label(relationship.source_label)
    _validate_label(relationship.target_label)
    _validate_rel_type(relationship.rel_type)
    session.run(
        f"""
        MATCH (a:{relationship.source_label} {{id: $source_id}})
        MATCH (b:{relationship.target_label} {{id: $target_id}})
        MERGE (a)-[r:{relationship.rel_type}]->(b)
        SET r += $properties
        """,
        {
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
            "properties": relationship.properties,
        },
    ).consume()


def _write_graph_meta(session, source_chunk_count: int) -> None:
    session.run(
        """
        MERGE (m:GraphMeta {id: 'latest'})
        SET m.rebuilt_at = datetime(),
            m.source_chunk_count = $source_chunk_count
        """,
        {"source_chunk_count": source_chunk_count},
    ).consume()


def _latest_index_run() -> dict[str, Any] | None:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, status, started_at, finished_at, source,
                       total_files, indexed_files, chunk_count, error_message
                FROM index_runs
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            row = cursor.fetchone()
    if not row:
        return None
    return dict(row)


def _add_node(nodes: dict[tuple[str, str], GraphNode], node: GraphNode) -> None:
    nodes[(node.label, node.id)] = node


def _add_rel(
    relationships: dict[tuple[str, str, str, str, str], GraphRelationship],
    source: GraphNode,
    rel_type: str,
    target: GraphNode,
    properties: dict[str, Any],
) -> None:
    key = (source.label, source.id, rel_type, target.label, target.id)
    relationships[key] = GraphRelationship(
        source_label=source.label,
        source_id=source.id,
        rel_type=rel_type,
        target_label=target.label,
        target_id=target.id,
        properties=properties,
    )


def _article_node(file_path: str, heading: str) -> GraphNode | None:
    if not file_path.lower().endswith(".md"):
        return None
    if not (file_path.startswith("content/") or file_path.startswith("cases/2026/")):
        return None
    title = heading.strip("# ").strip() or PurePosixPath(file_path).stem
    return GraphNode(
        label="Article",
        id=file_path,
        properties={"id": file_path, "path": file_path, "title": title},
    )


def _case_node(file_path: str, heading: str, text: str) -> GraphNode | None:
    if file_path.startswith("cases/"):
        case_id = PurePosixPath(file_path).stem
    else:
        match = CASE_RE.search(text)
        if not match or not match.group(1).upper().startswith("CASE-"):
            return None
        case_id = match.group(1)
    title = heading.strip("# ").strip() or case_id
    return GraphNode(
        label="Case",
        id=case_id,
        properties={"id": case_id, "title": title, "path": file_path},
    )


def _product_node(file_path: str, heading: str, text: str) -> GraphNode | None:
    name = _first_clean_match(PRODUCT_FIELD_RE, text)
    if not name and file_path.startswith("cases/2026/"):
        stem = PurePosixPath(file_path).stem
        parts = [part for part in re.split(r"[-_]", stem) if not part.isdigit()]
        if parts:
            name = " ".join(parts[:4])
    if not name:
        return None
    return GraphNode(
        label="Product",
        id=name,
        properties={"id": name, "name": name, "source_path": file_path},
    )


def _frameworks_in_text(text: str) -> list[str]:
    return sorted({term for term in FRAMEWORK_TERMS if term.lower() in text.lower()})


def _theories_in_text(text: str) -> list[str]:
    found = {term for term in THEORY_TERMS if term.lower() in text.lower()}
    for match in THEORY_RE.finditer(text):
        value = _clean_value(match.group(1))
        if value:
            found.add(value)
    return sorted(found)


def _first_clean_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return _clean_value(match.group(1))


def _clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def _file_kind(file_path: str) -> str:
    if file_path.startswith("cases/"):
        return "case"
    if file_path.startswith("core/"):
        return "core"
    if file_path.startswith("content/"):
        return "content"
    if file_path.startswith("ops/"):
        return "ops"
    return "file"


def _count_by_label(nodes: list[GraphNode]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.label] = counts.get(node.label, 0) + 1
    return counts


def _count_by_rel_type(relationships: list[GraphRelationship]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relationship in relationships:
        counts[relationship.rel_type] = counts.get(relationship.rel_type, 0) + 1
    return counts


def _validate_label(label: str) -> None:
    if label not in NODE_LABELS:
        raise ValueError(f"Unsupported node label: {label}")


def _validate_rel_type(rel_type: str) -> None:
    if rel_type not in REL_TYPES:
        raise ValueError(f"Unsupported relationship type: {rel_type}")
