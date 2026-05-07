from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class MarkdownChunk:
    file_path: str
    heading: str | None
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    ordinal: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_markdown(file_path: str, content: str) -> list[MarkdownChunk]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[MarkdownChunk] = []
    in_fence = False
    current_start = 1
    current_heading: str | None = None
    current_type = "document"

    def emit(end_line: int) -> None:
        nonlocal current_start, current_heading, current_type
        if end_line < current_start:
            return
        block_lines = lines[current_start - 1 : end_line]
        block = "\n".join(block_lines).strip()
        if not block:
            return
        chunks.append(
            MarkdownChunk(
                file_path=file_path,
                heading=current_heading,
                content=block,
                start_line=current_start,
                end_line=end_line,
                chunk_type=current_type,
                ordinal=len(chunks),
            )
        )

    for line_number, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue

        match = HEADING_RE.match(line)
        if in_fence or not match:
            continue

        if line_number > current_start:
            emit(line_number - 1)

        level = len(match.group(1))
        text = match.group(2).strip()
        current_start = line_number
        current_heading = text
        current_type = f"heading_{level}"

    emit(len(lines))
    return chunks
