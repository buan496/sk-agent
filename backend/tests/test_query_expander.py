from __future__ import annotations

from app.services.query_expander import expand_search_queries


def test_deep_research_expands_hippocratic_to_company_queries() -> None:
    queries = expand_search_queries(
        role_id="deep_researcher_role",
        task_type="deep_research",
        user_input="hippocratic",
    )

    assert queries == [
        "Hippocratic AI",
        "Hippocratic AI startup",
        "Hippocratic AI healthcare",
        "Hippocratic AI founder",
        "Hippocratic AI funding",
    ]


def test_product_teardown_expands_business_queries() -> None:
    queries = expand_search_queries(
        role_id="product_teardown_role",
        task_type="product_teardown",
        user_input="Example Product",
        limit=6,
    )

    assert "Example Product pricing" in queries
    assert "Example Product revenue" in queries
    assert "Example Product funding" in queries
    assert "Example Product competitors" in queries
    assert "Example Product reviews reddit" in queries


def test_article_publish_check_expands_freshness_queries() -> None:
    queries = expand_search_queries(
        role_id="article_publish_check_role",
        task_type="article_publish_check",
        user_input="Example Product",
    )

    assert queries == [
        "Example Product",
        "Example Product latest",
        "Example Product official",
        "Example Product announcement",
    ]


def test_explicit_queries_win_over_expansion() -> None:
    queries = expand_search_queries(
        role_id="deep_researcher_role",
        task_type="deep_research",
        user_input="hippocratic",
        explicit_queries=["custom official source", "custom reviews"],
    )

    assert queries == ["custom official source", "custom reviews"]
