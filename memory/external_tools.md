# External Tools

## Claude

- role: Long-form reasoning, writing revision, repository collaboration.
- when_to_use: Long context synthesis, article restructuring, deep narrative work.
- allowed_actions: Draft, critique, summarize, propose changes.
- forbidden_actions: Treat output as SK state without current repository reads.
- review_required: Always.

## Codex

- role: Engineering implementation, tests, API, frontend, documentation.
- when_to_use: sk-agent code changes, verification, Docker, docs.
- allowed_actions: Modify sk-agent code and docs when requested, run tests.
- forbidden_actions: Automatically modify SK content repository or push without instruction.
- review_required: For behavior changes and any generated patch draft.

## Hermes / Cursor

- role: Repository automation, batch edits, PR drafts.
- when_to_use: Large mechanical edits, execution of reviewed changes, PR preparation.
- allowed_actions: Apply reviewed patch plans and produce PR drafts.
- forbidden_actions: Bypass human review, silently change canonical files.
- review_required: Always.
