from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceClassification:
    source_type: str
    source_reason: str


APP_STORE_DOMAINS = {"play.google.com", "apps.apple.com"}
COMPANY_PROFILE_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "crunchbase.com",
    "www.crunchbase.com",
    "pitchbook.com",
    "www.pitchbook.com",
    "wellfound.com",
    "www.wellfound.com",
}
MEDIA_DOMAINS = {
    "techcrunch.com",
    "www.techcrunch.com",
    "wired.com",
    "www.wired.com",
    "theverge.com",
    "www.theverge.com",
    "businesswire.com",
    "www.businesswire.com",
    "prnewswire.com",
    "www.prnewswire.com",
    "forbes.com",
    "www.forbes.com",
    "36kr.com",
    "www.36kr.com",
    "techbuzz.ai",
    "www.techbuzz.ai",
    "bloomberg.com",
    "www.bloomberg.com",
    "reuters.com",
    "www.reuters.com",
    "wsj.com",
    "www.wsj.com",
    "huxiu.com",
    "www.huxiu.com",
    "pingwest.com",
    "www.pingwest.com",
}
COMMUNITY_DOMAINS = {
    "reddit.com",
    "www.reddit.com",
    "news.ycombinator.com",
    "x.com",
    "twitter.com",
    "www.twitter.com",
    "quora.com",
    "www.quora.com",
    "zhihu.com",
    "www.zhihu.com",
    "medium.com",
    "www.medium.com",
}
KNOWN_OFFICIAL_DOMAINS = {
    "openai.com",
    "www.openai.com",
    "anthropic.com",
    "www.anthropic.com",
}


def classify_source(url: str, query: str = "", title: str = "", snippet: str = "") -> SourceClassification:
    domain = _domain(url)
    path = urlparse(url or "").path.lower()
    text = f"{title} {snippet}".lower()

    if domain in APP_STORE_DOMAINS:
        return SourceClassification("app_store", "Google Play app listing" if "play.google.com" in domain else "Apple App Store listing")

    if _is_company_profile(domain, path):
        return SourceClassification("company_profile", "company profile database")

    if domain in COMMUNITY_DOMAINS or any(domain.endswith(f".{item}") for item in COMMUNITY_DOMAINS):
        return SourceClassification("community", "community discussion")

    if domain in MEDIA_DOMAINS or any(domain.endswith(f".{item}") for item in MEDIA_DOMAINS):
        if domain.endswith("businesswire.com") or domain.endswith("prnewswire.com"):
            return SourceClassification("media", "company announcement wire")
        return SourceClassification("media", "media report")

    if domain in KNOWN_OFFICIAL_DOMAINS or _domain_matches_query_object(domain, query):
        return SourceClassification("official", "domain matches product official site")

    if any(marker in domain for marker in [".gov", ".edu"]) or any(
        marker in domain for marker in ["docs.", "developer.", "developers.", "help.", "support."]
    ):
        return SourceClassification("official", "official documentation or institutional domain")

    if "official" in text:
        return SourceClassification("official", "result text indicates official source")

    return SourceClassification("unknown", "unclassified source")


def _domain(url: str) -> str:
    parsed = urlparse(url or "")
    domain = (parsed.netloc or "").lower()
    if "@" in domain:
        domain = domain.rsplit("@", 1)[-1]
    return domain.split(":", 1)[0]


def _is_company_profile(domain: str, path: str) -> bool:
    if domain in {"linkedin.com", "www.linkedin.com"}:
        return path.startswith("/company/")
    return domain in COMPANY_PROFILE_DOMAINS or any(domain.endswith(f".{item}") for item in COMPANY_PROFILE_DOMAINS)


def _domain_matches_query_object(domain: str, query: str) -> bool:
    if not domain or not query:
        return False
    clean_domain = domain.removeprefix("www.")
    domain_stem = clean_domain.split(".", 1)[0]
    tokens = [_clean_token(item) for item in query.split()]
    tokens = [item for item in tokens if len(item) >= 3 and item not in {"pricing", "founder", "funding", "startup", "latest", "official", "reviews", "reddit"}]
    if clean_domain in {token for token in tokens if "." in token}:
        return True
    return bool(domain_stem and any(domain_stem == token or domain_stem in token or token in domain_stem for token in tokens))


def _clean_token(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum() or char in {".", "-"}).strip(".-")
