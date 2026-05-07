from __future__ import annotations

from app.services.graph_builder import build_graph


def test_build_graph_extracts_core_nodes_and_relationships() -> None:
    rows = [
        {
            "file_path": "cases/2026/015-chatgpt.md",
            "heading": "ChatGPT case",
            "content": "\n".join(
                [
                    "产品：ChatGPT",
                    "判为：工具",
                    "命中 FM015",
                    "使用 诊断空白 和 MTP 理论",
                ]
            ),
            "start_line": 10,
            "end_line": 20,
            "chunk_type": "section",
            "ordinal": 1,
        }
    ]

    graph = build_graph(rows)
    nodes = {(node.label, node.id) for node in graph["nodes"]}
    relationships = {
        (rel.source_label, rel.source_id, rel.rel_type, rel.target_label, rel.target_id)
        for rel in graph["relationships"]
    }

    assert ("File", "cases/2026/015-chatgpt.md") in nodes
    assert ("Article", "cases/2026/015-chatgpt.md") in nodes
    assert ("Case", "015-chatgpt") in nodes
    assert ("Product", "ChatGPT") in nodes
    assert ("Decision", "cases/2026/015-chatgpt.md#10#decision") in nodes
    assert ("FailureMode", "FM015") in nodes
    assert ("Framework", "诊断空白") in nodes
    assert ("Theory", "MTP") in nodes
    assert ("Case", "015-chatgpt", "TRIGGERS", "FailureMode", "FM015") in relationships
    assert (
        "Product",
        "ChatGPT",
        "HAS_DECISION",
        "Decision",
        "cases/2026/015-chatgpt.md#10#decision",
    ) in relationships


def test_build_graph_deduplicates_nodes() -> None:
    rows = [
        {
            "file_path": "cases/2026/001-example.md",
            "heading": "A",
            "content": "产品：Example\nFM001\n诊断空白",
            "start_line": 1,
            "end_line": 3,
            "chunk_type": "section",
            "ordinal": 1,
        },
        {
            "file_path": "cases/2026/001-example.md",
            "heading": "B",
            "content": "产品：Example\nFM001\n诊断空白",
            "start_line": 4,
            "end_line": 6,
            "chunk_type": "section",
            "ordinal": 2,
        },
    ]

    graph = build_graph(rows)
    product_nodes = [node for node in graph["nodes"] if node.label == "Product" and node.id == "Example"]
    failure_nodes = [node for node in graph["nodes"] if node.label == "FailureMode" and node.id == "FM001"]

    assert len(product_nodes) == 1
    assert len(failure_nodes) == 1
