# Phase 9.2 多智能体记忆与路由系统

## 本阶段目标

建立轻量多智能体记忆系统，用来记录：

- 哪类任务该交给哪个 AI / GPTS / 工具
- 哪个外部 AI 做过什么
- 输出是否已经入库
- 结果关联哪些 SK 文件
- 哪些经验需要沉淀成 SOP
- 哪些输出只是候选材料，不能当作当前状态

本阶段暂停 Phase 9.1 UI 优化，不重做前端视觉。

## 新增文件

```text
memory/core_memory.md
memory/constitution.md
memory/agent_registry.md
memory/gpts_registry.md
memory/external_tools.md
memory/episodes/drift-log.md
memory/episodes/agent-lessons.md
memory/episodes/routing-lessons.md
docs/multi-agent-routing.md
docs/phase-9-2-multi-agent-memory.md
```

## 新增数据库表

```text
external_agent_runs
```

字段：

- `id`
- `created_at`
- `agent_type`
- `agent_name`
- `task_type`
- `input_summary`
- `output_summary`
- `source_link_or_file`
- `related_sk_files_json`
- `status`
- `should_ingest`
- `ingested`
- `notes`

该表只记录外部 AI / GPTS / Claude / Codex / Hermes / Cursor 等任务结果，不进入 SK 内容索引。

## 新增 API

```text
GET /memory/core
GET /memory/registries
GET /memory/episodes
POST /memory/external-run
GET /memory/external-runs?limit=20
```

## 多智能体路由规则

- 需要外部事实证据 -> GPTS 深度研究员
- 需要长文改写 / 推演 -> Claude
- 需要工程实现 -> Codex
- 需要批量改文件 -> Hermes / Cursor
- 需要当前状态校准 -> sk-agent
- 需要任务路由判断 -> ChatGPT Project
- 需要可审核入库材料 -> sk-agent `/patch/draft`

## 记忆优先级

1. canonical files
2. 当前 SK 仓库中本次读取到的相关文件
3. PostgreSQL chunks / 检索结果
4. Neo4j graph
5. `memory/` 规约与 lessons
6. `external_agent_runs`
7. 外部 AI 原始输出

## 为什么 canonical files 仍然最高优先级

canonical files 是 SK 当前状态的 SSOT：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

memory、graph、vector、external_agent_runs 都只能辅助判断。外部 AI 输出未入库前，不代表 SK 当前状态。

## 如何记录一次 GPTS / Claude / Codex 外部任务

调用：

```text
POST /memory/external-run
```

示例字段：

```json
{
  "agent_type": "gpts",
  "agent_name": "深度研究员",
  "task_type": "external_research",
  "input_summary": "研究某产品是否值得纳入 SK。",
  "output_summary": "收集到候选证据，但尚未入库。",
  "source_link_or_file": "https://example.com/research",
  "related_sk_files": ["cases/2026/case-index.md"],
  "status": "reviewed",
  "should_ingest": true,
  "ingested": false,
  "notes": "需要生成 patch draft 后人工复核。"
}
```

## 尚未完成的问题

- 还没有持久化 sk-agent 自身的 `agent_runs` 表；当前 Phase 9.2 只新增 `external_agent_runs`。
- 前端 Memory 页面只是最小入口，没有做复杂筛选和统计。
- 外部任务记录不会自动触发入库流程，需要用户手动生成 patch draft。
- `memory/` 是规约记忆，不是事实库，不能覆盖 canonical files。
