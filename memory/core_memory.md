# SK Agent Core Memory

## Long-Term Principles

- Always read canonical files before answer-type work.
- Canonical files are the highest-priority source of current SK state.
- Every Agent output must include `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, and `answer_markdown`.
- Do not automatically write to the SK repository.
- Generate patch drafts for human review when content should be ingested.
- Graph, vector search, memory, and external agent logs are advisory only.
- External AI outputs are candidate material until reviewed and ingested into SK.

## Canonical Files

- `README.md`
- `ops/执行状态总表.md`
- `cases/2026/case-index.md`
- `cases/2026/case-cards.md`

## Non-Override Rule

Memory can guide routing and workflow habits, but memory never overrides canonical files.
