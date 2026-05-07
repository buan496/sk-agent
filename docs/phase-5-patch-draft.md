# Phase 5: Patch Draft Generator

Status: complete for the local-first draft workflow.

## Goal

Generate reviewable SK repository draft material without writing to GitHub or the local SK repository.

The endpoint reads the current target file first, records what was read, and then returns:

- suggested save path
- Markdown body
- diff summary
- diff preview
- commit message
- PR title
- PR body
- risk notes

## API

```text
POST /patch/draft
```

Request:

```json
{
  "target_file": "cases/2026/example.md",
  "intent": "新增轻量初拆文档",
  "new_content": "# Example\n\n正文内容",
  "operation": "auto"
}
```

`operation` supports:

- `auto`: append when the file is read, create when the file is not read
- `create`: generate a new-file draft
- `append`: append content to the target file
- `replace`: replace the full target file in the draft

## Safety Rules

- The service does not write files.
- The service does not call GitHub write APIs.
- If the target file is not read, the response keeps the phase 1 rule: this means only "not read this time", not "file does not exist".
- `replace` returns an explicit risk note because it is a full-file draft.

## Verification

```powershell
docker compose build backend
docker compose run --rm backend pytest
```

Current result:

```text
22 passed
```
