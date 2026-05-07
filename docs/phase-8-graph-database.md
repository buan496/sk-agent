# Phase 8: Graph Database

Status: first Neo4j-backed graph version complete.

## Goal

Build a queryable SK knowledge graph after phases 0-7 are already running.

## Stack

- Neo4j 5 Community in Docker Compose
- Python Neo4j driver in the backend
- PostgreSQL chunks as the source of graph rebuild

## Nodes

Implemented labels:

- `Product`
- `Case`
- `Article`
- `Framework`
- `FailureMode`
- `Theory`
- `File`
- `Decision`
- `Signal`

## Relationships

Implemented relationship types:

- `APPEARS_IN`
- `TRIGGERS`
- `USES`
- `REFERENCES`
- `HAS_DECISION`

## APIs

```text
POST /graph/rebuild
GET /graph/status
GET /graph/failure-modes/{code}/cases
GET /graph/frameworks/articles?framework=诊断空白
GET /graph/products/tools
GET /graph/theories/reused?min_cases=2
```

## Rebuild Flow

1. Read indexed chunks from PostgreSQL.
2. Extract graph nodes and relationships with deterministic rules.
3. Clear the current Neo4j graph.
4. Write nodes and relationships to Neo4j.

## Verification

```powershell
docker compose build backend
docker compose run --rm --no-deps backend pytest
docker compose up -d --build backend
Invoke-RestMethod -Method Post http://localhost:8000/graph/rebuild
Invoke-RestMethod http://localhost:8000/graph/status
```

Current rebuild result:

```text
source_chunk_count=3703
node_count=535
relationship_count=1358
```

Current graph status:

```text
Article=84
Case=79
Decision=15
FailureMode=15
File=170
Framework=9
Product=93
Signal=46
Theory=24
```

## Acceptance Questions

```text
哪些案例命中 FM015？
GET /graph/failure-modes/FM015/cases

诊断空白框架出现在哪些文章？
GET /graph/frameworks/articles?framework=诊断空白

哪些产品被判为“工具”？
GET /graph/products/tools

哪些理论被多个案例引用？
GET /graph/theories/reused
```

## Boundaries

- Graph extraction is deterministic and conservative.
- The graph is rebuilt from the PostgreSQL index; rebuild `/index/rebuild` first when repository content changes.
- No GitHub write API is used.
- No local SK repository files are modified.
