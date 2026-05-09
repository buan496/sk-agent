from __future__ import annotations

from app.services.evidence_classifier import web_result_to_evidence
from app.services.source_classifier import classify_source


def test_official_domain_matches_query_object() -> None:
    result = classify_source("https://myhair.ai", query="myhair ai pricing")

    assert result.source_type == "official"
    assert result.source_reason == "domain matches product official site"


def test_app_store_classification_and_metadata_candidate() -> None:
    result = classify_source("https://play.google.com/store/apps/details?id=com.example", query="myhair reviews")
    evidence = web_result_to_evidence(
        "app metadata",
        {
            "title": "MyHair app rating reviews",
            "url": "https://play.google.com/store/apps/details?id=com.example",
            "snippet": "Rating and reviews updated",
            "source_type": result.source_type,
            "source_reason": result.source_reason,
        },
    )

    assert result.source_type == "app_store"
    assert evidence["evidence_level"] == "A_candidate_for_app_metadata"


def test_company_profile_classification() -> None:
    linkedin = classify_source("https://www.linkedin.com/company/myhair-ai", query="myhair ai")
    crunchbase = classify_source("https://www.crunchbase.com/organization/myhair-ai", query="myhair ai")

    assert linkedin.source_type == "company_profile"
    assert crunchbase.source_type == "company_profile"
    assert linkedin.source_reason == "company profile database"


def test_media_and_announcement_wire_classification() -> None:
    pr = classify_source("https://www.prnewswire.com/news-releases/example.html", query="example announcement")
    evidence = web_result_to_evidence(
        "announcement",
        {
            "title": "Company announces launch",
            "url": "https://www.prnewswire.com/news-releases/example.html",
            "snippet": "announcement",
            "source_type": pr.source_type,
            "source_reason": pr.source_reason,
        },
    )

    assert pr.source_type == "media"
    assert pr.source_reason == "company announcement wire"
    assert evidence["evidence_level"] == "A_candidate_for_announcement"


def test_community_and_unknown_classification() -> None:
    reddit = classify_source("https://www.reddit.com/r/startups/comments/example", query="myhair ai")
    unknown = classify_source("https://random-example-site.test/post", query="myhair ai")

    assert reddit.source_type == "community"
    assert reddit.source_reason == "community discussion"
    assert unknown.source_type == "unknown"
    assert unknown.source_reason == "unclassified source"
