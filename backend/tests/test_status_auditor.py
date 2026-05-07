from __future__ import annotations

from app.services.status_auditor import (
    _extract_article_statuses,
    _extract_case_cards,
    _extract_readme_publication_statuses,
    _status_bucket,
)


def test_extract_article_statuses() -> None:
    content = "012 ✅ 已发布\n015 ⏸️ 占位暂缓\n"

    result = _extract_article_statuses(content, "README.md")

    assert result["012"]["status"] == "已发布"
    assert result["015"]["status"] == "待发布"


def test_extract_case_cards_fields() -> None:
    content = """
## CASE-014 · Example

```yaml
case_id: "CASE-014-Example"
article_file: "cases/2026/014-example.md"
article_published: "2026-05-02"
depth_draft: "cases/2026/depth.md"
```
"""

    cards = _extract_case_cards(content)
    card = cards["CASE-014-Example"]

    assert card["article_id"] == "014"
    assert card["article_published"] == "2026-05-02"
    assert card["depth_draft"] == "cases/2026/depth.md"


def test_extract_readme_publication_statuses_from_section_only() -> None:
    content = """
006 elsewhere 待发布

## 发布状态

```
001 ✅ 已发布    015 ⏸️ 占位暂缓
016 ✅ 已重新分配
```

---
"""

    result = _extract_readme_publication_statuses(content)

    assert "006" not in result
    assert result["001"]["status"] == "已发布"
    assert result["015"]["status"] == "待发布"


def test_status_bucket() -> None:
    assert _status_bucket("已发布") == "published"
    assert _status_bucket("2026-05-02") == "published"
    assert _status_bucket("待发布") == "waiting"
