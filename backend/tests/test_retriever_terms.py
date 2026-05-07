from __future__ import annotations

from app.services.retriever import SearchHit, _diversify_hits, _query_terms


def test_query_terms_include_cjk_windows() -> None:
    terms = _query_terms("诊断空白四条件是什么？")

    assert "诊断空白四条件是什么" in terms
    assert "诊断" in terms
    assert "空白" in terms
    assert "条件" in terms
    assert "诊断空白" in terms


def test_query_terms_include_ascii_tokens() -> None:
    terms = _query_terms("MTP 构思招募法在哪")

    assert "MTP" in terms
    assert "构思" in terms


def test_query_terms_include_domain_aliases() -> None:
    terms = _query_terms("case-card 格式在哪里")

    assert "format" in terms
    assert "案例卡" in terms


def test_query_terms_extract_question_core_phrase() -> None:
    terms = _query_terms("产品评估决策清单有哪些必须条件")

    assert "产品评估决策清单" in terms
    assert "必须条件" in terms


def test_diversify_hits_caps_results_per_file_first() -> None:
    hits = [
        _hit("a.md", 10),
        _hit("a.md", 9),
        _hit("a.md", 8),
        _hit("b.md", 7),
    ]

    selected = _diversify_hits(hits, limit=3, per_file_limit=2)

    assert [hit.file_path for hit in selected] == ["a.md", "a.md", "b.md"]


def _hit(path: str, score: float) -> SearchHit:
    return SearchHit(
        chunk_id=int(score),
        file_path=path,
        heading=None,
        content="content",
        start_line=1,
        end_line=1,
        chunk_type="document",
        keyword_score=score,
        file_priority_score=0,
        total_score=score,
    )
