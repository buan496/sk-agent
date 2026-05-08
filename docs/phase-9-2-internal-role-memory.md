# Phase 9.2 内部多角色记忆与路由系统

## 新增文件

```text
backend/app/roles/base_role.py
backend/app/roles/role_registry.py
backend/app/roles/role_router.py
backend/app/roles/deep_researcher_role.py
backend/app/roles/writing_workshop_role.py
backend/app/roles/first_reader_role.py
backend/app/roles/product_teardown_role.py
backend/app/roles/repo_governance_role.py
backend/app/roles/patch_writer_role.py
backend/app/api/roles.py
memory/internal_roles.md
memory/episodes/role-lessons.md
docs/internal-role-system.md
docs/phase-9-2-internal-role-memory.md
```

## 新增 API

```text
GET /roles
POST /roles/run
GET /roles/runs?limit=10
```

## 新增数据库表

```text
internal_role_runs
```

字段：

- `id`
- `created_at`
- `role_id`
- `role_name`
- `task_type`
- `input_summary`
- `read_files_json`
- `structured_output_json`
- `conclusion`
- `risks_json`
- `minimal_next_step`
- `answer_markdown`
- `should_ingest`
- `ingested`
- `notes`

## 内部角色列表

- `deep_researcher_role`
- `writing_workshop_role`
- `first_reader_role`
- `product_teardown_role`
- `repo_governance_role`
- `patch_writer_role`

## 角色路由规则

- `deep_research` -> `deep_researcher_role`
- `writing_workshop` -> `writing_workshop_role`
- `first_reader` -> `first_reader_role`
- `product_teardown` -> `product_teardown_role`
- `repo_governance` -> `repo_governance_role`
- `patch_draft` -> `patch_writer_role`
- `status_audit` -> `repo_governance_role`
- `article_publish_check` -> `writing_workshop_role`

## 记忆层级

1. canonical files
2. 当前 SK 仓库本次读取文件
3. PostgreSQL chunks / 检索结果
4. Neo4j graph
5. 内部角色运行记录
6. memory 文件
7. 外部 GPTS / Claude / Codex / Hermes 输出

## 如何运行内部角色

```http
POST /roles/run
```

示例：

```json
{
  "task_type": "deep_research",
  "input": "研究某个产品是否值得进入 SK",
  "notes": "",
  "preferred_role": null
}
```

每次运行都会先执行 canonical preflight，并写入 `internal_role_runs`。

## 如何查看角色运行记录

```http
GET /roles/runs?limit=10
```

## 未完成事项

- 内部角色当前是轻量 deterministic 版本，暂不引入复杂多 Agent 编排。
- 没有引入 LangGraph、Mem0、Zep、Letta。
- 外部工具仍作为外援记录存在，但不是 Phase 9.2 主线。
- 角色运行记录不代表 SK 当前状态，只有入库后的 SK 文件才代表当前状态。
