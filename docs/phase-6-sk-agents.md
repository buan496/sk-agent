# Phase 6: SK Workflow Agents

Status: first usable backend version complete.

## Goal

Provide three SK-specific workflows on top of the local-first repository reader:

- Product teardown
- Framework red team
- Article publish check

Each workflow reads current repository files first and returns the read file list before giving a judgment or draft.

## APIs

```text
POST /agents/product-teardown
POST /agents/framework-red-team
POST /agents/article-publish-check
```

## Product Teardown

Request:

```json
{
  "product_name": "Example Product",
  "notes": "optional context",
  "limit": 8
}
```

Workflow:

- runs status audit
- searches the repository for existing product mentions
- reads product teardown templates
- asks MiniMax to generate a lightweight teardown when configured
- falls back to a deterministic skeleton when MiniMax is unavailable
- returns whether the draft should be ingested or deduplicated first

## Framework Red Team

Request:

```json
{
  "idea": "AI product idea",
  "notes": "optional context",
  "limit": 8
}
```

Workflow:

- reads the project questioning checklist
- reads the product evaluation decision checklist
- reads `core/failure_modes.yml`
- searches related repository context
- outputs reverse risk clearing and a Kill / Go / Hold judgment

## Article Publish Check

Request:

```json
{
  "final_article": "# Title\n\nArticle body",
  "notes": "optional context",
  "limit": 8
}
```

Workflow:

- reads writing guide candidates
- reads content production handbook candidates
- reads article publish SOP candidates
- searches related repository context
- outputs risk check and a publish package

## Verification

```powershell
docker compose build backend
docker compose run --rm backend pytest
```

Current result:

```text
26 passed
```

## Boundaries

- No graph database.
- No automatic GitHub write.
- No direct SK repository write.
- MiniMax failure does not break the workflow; the API returns a rules-based skeleton and reports `llm.status=unavailable`.
