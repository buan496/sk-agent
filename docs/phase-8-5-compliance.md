# Phase 8.5 规约收口与双仓边界合规报告

## 修改了哪些文件

- `backend/app/services/canonical_preflight.py`：新增统一 canonical preflight 与读取记录合并工具。
- `backend/app/api/search.py`、`backend/app/services/qa_service.py`：为 `/ask` 接入 canonical preflight。
- `backend/app/api/agents.py`、`backend/app/services/sk_workflow_agents.py`、`backend/app/services/status_auditor.py`：为 Agent 接口接入 preflight，并固化输出 schema。
- `backend/app/api/graph.py`、`backend/app/services/graph_builder.py`：为 `/graph/status` 增加图谱新鲜度与 canonical 读取状态。
- `backend/app/config.py`、`.env.example`、`docker-compose.yml`：增加 SK / SKGPT 双仓环境变量。
- `backend/app/services/indexer.py`：跳过常见 SKGPT 配置目录，避免混入 SK 内容索引。
- `frontend/app/page.tsx`：显示 Agent schema 字段，并保存最近 10 次 Agent 执行记录。
- `backend/tests/test_sk_workflow_agents.py`：补充 Agent schema 与 canonical 顺序断言。
- `docs/architecture.md`、`docs/phase-8-graph-database.md`：补充双仓边界和图谱辅助层原则。

## 哪些接口已加 preflight

- `POST /ask`
- `POST /agents/status-audit`
- `POST /agents/product-teardown`
- `POST /agents/framework-red-team`
- `POST /agents/article-publish-check`

以上接口的 `read_files` 会优先包含 4 个 canonical 文件读取记录。读取失败时只标记“本次未读取到”，不推断文件不存在。

## 哪些 Agent 已 schema 化

- `status_audit`
- `product_teardown`
- `framework_red_team`
- `article_publish_check`

统一字段至少包括：

- `conclusion`
- `read_files`
- `evidence`
- `risks`
- `minimal_next_step`
- `ingest_draft`
- `answer_markdown`

## 哪些测试通过

```powershell
docker compose run --rm backend pytest
```

结果：`33 passed`

```powershell
docker compose run --rm frontend npm run build
```

结果：Next.js production build 通过。

```powershell
Invoke-RestMethod http://localhost:8000/graph/status
Invoke-RestMethod -Method Post http://localhost:8000/agents/status-audit -Body '{}'
```

结果：`/graph/status` 已返回 `latest_index_run` 与 `canonical_read_status`；`/agents/status-audit` 已返回 7 个固定 schema 字段。

## 仍未完成的问题

- `/ask` 当前仍是基础问答接口，不强制使用 Agent schema；本期只要求它接入 canonical preflight。
- 图谱新鲜度依赖 `/graph/rebuild` 后写入的 `GraphMeta`。如果还没重建图谱，`graph_rebuild_time` 与 `source_chunk_count` 可能为空。
- SKGPT 目前只做边界变量与索引隔离预留，还没有实现 SKGPT 仓库读取工作流。
- 本期没有实现自动 commit、自动 PR、自动 GitHub 写入，也没有新增 Agent。
