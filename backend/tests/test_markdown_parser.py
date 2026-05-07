from __future__ import annotations

from app.services.markdown_parser import parse_markdown


def test_parse_markdown_splits_by_headings() -> None:
    content = "\n".join(
        [
            "intro",
            "",
            "# One",
            "body",
            "## Two",
            "more",
        ]
    )

    chunks = parse_markdown("README.md", content)

    assert len(chunks) == 3
    assert chunks[0].heading is None
    assert chunks[0].chunk_type == "document"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2
    assert chunks[1].heading == "One"
    assert chunks[1].chunk_type == "heading_1"
    assert chunks[2].heading == "Two"
    assert chunks[2].start_line == 5


def test_parse_markdown_ignores_headings_inside_code_fences() -> None:
    content = "\n".join(
        [
            "# Real",
            "```",
            "# Not heading",
            "```",
            "text",
        ]
    )

    chunks = parse_markdown("README.md", content)

    assert len(chunks) == 1
    assert chunks[0].heading == "Real"
    assert "# Not heading" in chunks[0].content
