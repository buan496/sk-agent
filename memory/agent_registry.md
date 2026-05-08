# Internal Agent Registry

## repo_qa_agent

- role: Answer questions using current SK files.
- use_cases: Concept lookup, file citation, current repository Q&A.
- required_inputs: User question.
- required_read_files: Canonical files plus retrieved SK files.
- output_schema: `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, `answer_markdown`.
- limitations: Cannot invent missing evidence.

## status_agent

- role: Detect SK state drift.
- use_cases: README/status table/case index/case card consistency checks.
- required_inputs: None.
- required_read_files: The four canonical files.
- output_schema: `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, `answer_markdown`.
- limitations: Rule-based extraction may miss ambiguous prose.

## teardown_agent

- role: Produce product lightweight teardown drafts.
- use_cases: New product analysis, duplicate checks, intake drafts.
- required_inputs: Product name and optional notes.
- required_read_files: Canonical files, teardown templates, relevant SK matches.
- output_schema: `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, `answer_markdown`.
- limitations: Must not bypass duplicate checks or state audit.

## framework_red_team_agent

- role: Stress-test an idea with SK frameworks and failure modes.
- use_cases: Kill/Go/Hold review, risk discovery, evidence gaps.
- required_inputs: Project idea or product direction.
- required_read_files: Canonical files, project interrogation checklist, product evaluation checklist, failure modes.
- output_schema: `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, `answer_markdown`.
- limitations: Does not replace external fact research.

## article_publish_check_agent

- role: Check an article draft before publication.
- use_cases: Risk check, publish package, title/summary/tag checklist.
- required_inputs: Article final draft and optional notes.
- required_read_files: Canonical files, writing guide, content production handbook, publish SOP.
- output_schema: `conclusion`, `read_files`, `evidence`, `risks`, `minimal_next_step`, `ingest_draft`, `answer_markdown`.
- limitations: Cannot confirm external facts without cited evidence.
