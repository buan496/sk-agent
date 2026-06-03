# System Inventory Audit

## 1. 总结论

当前 sk-agent 后端能力大部分仍然存在，但前端主入口已经被 Phase 11 的 Cognitive Flow 页面覆盖。

结论：

- 后端 API：大部分保留，未删除。
- 数据库：当前实际存在 12 张表。
- 前端：当前 `frontend/app/page.tsx` 只暴露 Cognitive Flow 入口。
- 原工作台入口：文件、检索、审计、Agent、Patch、Graph、Memory、Internal Roles 等旧入口已从当前首页隐藏。
- Research State：后端存在，但前端没有独立页面。
- Intent Router：未发现独立实现；当前只是 Cognitive Flow 内部轻量判断。
- `allow_web` 默认是 `false`，这是安全的。
- Repo Inventory：未发现独立“系统库存/模块盘点”功能，本次报告是手工审计生成。

当前系统不是“原工作台”，也不是“Internal Roles”，而是默认进入：

```text
Cognitive Flow
```

最大问题不是后端能力丢失，而是前端入口被替换后，用户看不到旧功能。

## 2. 当前后端 API 清单

### Health

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/health` | 健康检查 | 否 | 否 | `backend/app/main.py` |

### Repo

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/repo/files` | 列出 SK 仓库文件树 | 否，已隐藏 | 否 | `backend/app/api/repo.py` |
| GET | `/repo/file?path=` | 读取单个 SK 文件 | 否，已隐藏 | 否 | `backend/app/api/repo.py` |
| GET | `/repo/canonical` | 读取 4 个 canonical files | 间接使用：`/cognitive/think` 内部 preflight | 否 | `backend/app/api/repo.py` |
| POST | `/repo/sync` | 拉取 / 同步本地 SK 仓库 | 否，按钮已隐藏 | 否 | `backend/app/api/repo.py` |

### Index

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/index/rebuild` | 重建 Markdown 索引 | 否，按钮已隐藏 | 否 | `backend/app/api/index.py` |
| GET | `/index/status` | 查看索引状态 | 否，已隐藏 | 否 | `backend/app/api/index.py` |
| GET | `/index/chunks?file_path=` | 查看文件 chunks | 否，已隐藏 | 否 | `backend/app/api/index.py` |

### Search / Ask

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/search` | 关键词检索 chunks | 否，搜索页已隐藏 | 否 | `backend/app/api/search.py` |
| POST | `/ask` | 基于索引和 canonical preflight 的问答 | 否，问答页已隐藏 | 否 | `backend/app/api/search.py` |

### SK Workflow Agents

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/agents/status-audit` | 状态漂移审计 | 否，入口已隐藏 | 否 | `backend/app/api/agents.py` |
| POST | `/agents/product-teardown` | 产品轻量初拆 | 否，入口已隐藏 | 否 | `backend/app/api/agents.py` |
| POST | `/agents/framework-red-team` | 框架红队 | 否，入口已隐藏 | 否 | `backend/app/api/agents.py` |
| POST | `/agents/article-publish-check` | 文章发布检查 | 否，入口已隐藏 | 否 | `backend/app/api/agents.py` |

### Patch

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/patch/draft` | 生成可审核入库稿草案 | 否，入口已隐藏 | 否 | `backend/app/api/patch.py` |

### Graph

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/graph/rebuild` | 从 chunks 重建 Neo4j 图谱 | 否，按钮已隐藏 | 否 | `backend/app/api/graph.py` |
| GET | `/graph/status` | 查看图谱状态和 canonical read status | 否，已隐藏 | 否 | `backend/app/api/graph.py` |
| GET | `/graph/failure-modes/{code}/cases` | 查命中某 failure mode 的案例 | 否，已隐藏 | 否 | `backend/app/api/graph.py` |
| GET | `/graph/frameworks/articles?framework=` | 查框架出现在哪些文章 | 否，已隐藏 | 否 | `backend/app/api/graph.py` |
| GET | `/graph/products/tools` | 查被判为工具的产品 | 否，已隐藏 | 否 | `backend/app/api/graph.py` |
| GET | `/graph/theories/reused` | 查被多个案例引用的理论 | 否，已隐藏 | 否 | `backend/app/api/graph.py` |

### Memory

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/memory/core` | 读取 core memory / constitution | 否，已隐藏 | 否 | `backend/app/api/memory.py` |
| GET | `/memory/registries` | 读取角色 / GPTS / 外部工具注册表 | 否，已隐藏 | 否 | `backend/app/api/memory.py` |
| GET | `/memory/episodes` | 读取 drift / lessons | 否，已隐藏 | 否 | `backend/app/api/memory.py` |
| POST | `/memory/external-run` | 记录外部 AI 任务 | 否，入口已隐藏 | 可选保留 | `backend/app/api/memory.py` |
| GET | `/memory/external-runs?limit=` | 查看外部 AI 任务记录 | 否，入口已隐藏 | 可选保留 | `backend/app/api/memory.py` |

### Internal Roles

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/roles` | 查看内部角色列表 | 否，页面已隐藏 | 否 | `backend/app/api/roles.py` |
| POST | `/roles/run` | 显式运行内部角色 | 否，入口已隐藏；但 `/cognitive/think` 可内部调用 | 否 | `backend/app/api/roles.py` |
| GET | `/roles/runs?limit=` | 查看 internal_role_runs | 否，入口已隐藏 | 否 | `backend/app/api/roles.py` |

### Web

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/web/search` | Tavily / mock 联网搜索 | 否；Cognitive Flow 通过 role operator 间接使用 | 否 | `backend/app/api/web.py` |
| POST | `/web/read-source` | 读取来源正文 | 否；Cognitive Flow 可通过 operator/source reader 间接使用 | 否 | `backend/app/api/web.py` |

### Research

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/research/objects` | 创建 / 获取 research object | 否；Cognitive Flow 内部自动调用 | 否 | `backend/app/api/research.py` |
| GET | `/research/objects?limit=` | 列出 research objects | 否，未接前端 | 否 | `backend/app/api/research.py` |
| GET | `/research/objects/{slug}/state` | 查看研究状态 | 否，未接独立前端 | 否 | `backend/app/api/research.py` |
| POST | `/research/objects/{slug}/sources` | 手动添加候选来源 | 否，未接前端 | 可选保留 | `backend/app/api/research.py` |
| POST | `/research/objects/{slug}/read-source` | 读取来源并沉淀候选事实 | 否，未接前端 | 否 | `backend/app/api/research.py` |
| POST | `/research/objects/{slug}/ingest-role-run` | 导入 internal role run 到研究状态 | 否，未接前端；Cognitive Flow 内部自动调用 | 可选保留 | `backend/app/api/research.py` |

### Cognitive

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| POST | `/cognitive/think` | 当前主入口：连续认知流 | 是 | 否 | `backend/app/api/cognitive.py` |
| GET | `/cognitive/sessions?limit=` | 最近 cognitive sessions | 是 | 否 | `backend/app/api/cognitive.py` |
| GET | `/cognitive/sessions/{session_id}/state` | 读取某个认知会话状态 | 是 | 否 | `backend/app/api/cognitive.py` |

### LLM

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/llm/config` | 查看 LLM 配置摘要，不泄露 key | 否，已隐藏 | 可选保留 | `backend/app/api/llm.py` |
| POST | `/llm/chat` | 低层 LLM chat 调用 | 否，已隐藏 | 可选保留 / 调试用 | `backend/app/api/llm.py` |

### SKGPT

| 方法 | 路径 | 用途 | 前端使用 | 是否废弃 | 后端文件 |
|---|---|---|---|---|---|
| GET | `/skgpt/files` | 列出 SKGPT 仓库文件 | 否，已隐藏 | 可选保留 | `backend/app/api/skgpt.py` |
| GET | `/skgpt/file?path=` | 读取 SKGPT 指令文件 | 否，已隐藏 | 可选保留 | `backend/app/api/skgpt.py` |
| GET | `/skgpt/role-prompts` | 读取角色 prompt 映射 | 否，已隐藏 | 可选保留 | `backend/app/api/skgpt.py` |

## 3. 当前数据库表清单

当前 PostgreSQL 实际表清单来自只读查询：

```text
chunks
cognitive_entities
cognitive_judgments
cognitive_messages
cognitive_sessions
external_agent_runs
files
index_runs
internal_role_runs
research_facts
research_objects
research_sources
```

### files

- 用途：保存已索引文件元信息。
- 写入接口：`POST /index/rebuild`
- 读取接口：`GET /index/status` 统计；`GET /index/chunks` 间接依赖；`/search` 和 `/ask` 主要读 chunks。
- 是否仍在使用：是。

### chunks

- 用途：保存 Markdown 切块。
- 写入接口：`POST /index/rebuild`
- 读取接口：`POST /search`、`POST /ask`、`GET /index/chunks`、`POST /graph/rebuild`
- 是否仍在使用：是。

### index_runs

- 用途：保存索引重建记录。
- 写入接口：`POST /index/rebuild`
- 读取接口：`GET /index/status`、`GET /graph/status`
- 是否仍在使用：是。

### external_agent_runs

- 用途：记录外部 GPTS / Claude / Codex / Hermes 等任务结果。
- 写入接口：`POST /memory/external-run`
- 读取接口：`GET /memory/external-runs`
- 是否仍在使用：后端可用；当前前端隐藏。
- 建议：可选保留。

### internal_role_runs

- 用途：记录 `/roles/run` 运行结果。
- 写入接口：`POST /roles/run`；`POST /cognitive/think` 在 `allow_web=true` 且调用 operator 时会间接写入。
- 读取接口：`GET /roles/runs`、`POST /research/objects/{slug}/ingest-role-run`、旧 conversation carryover 逻辑。
- 是否仍在使用：是，但前端显式入口隐藏。

### research_objects

- 用途：保存研究对象。
- 写入接口：`POST /research/objects`；`POST /cognitive/think` 自动创建 / 关联。
- 读取接口：`GET /research/objects`、`GET /research/objects/{slug}/state`、`POST /cognitive/think`
- 是否仍在使用：是，Cognitive Flow 内部使用。

### research_sources

- 用途：保存研究对象关联的候选来源和正文读取结果。
- 写入接口：`POST /research/objects/{slug}/sources`、`POST /research/objects/{slug}/read-source`、`POST /research/objects/{slug}/ingest-role-run`；`POST /cognitive/think` 在 operator 产出后可间接写入。
- 读取接口：`GET /research/objects/{slug}/state`、`POST /cognitive/think`
- 是否仍在使用：是，当前前端只显示计数，不提供管理页。

### research_facts

- 用途：保存从来源正文和候选 claims 抽出的候选事实。
- 写入接口：`POST /research/objects/{slug}/read-source`、`POST /research/objects/{slug}/ingest-role-run`
- 读取接口：`GET /research/objects/{slug}/state`、`POST /cognitive/think`
- 是否仍在使用：是，但前端仅显示研究状态计数。

### cognitive_sessions

- 用途：保存当前认知会话。
- 写入接口：`POST /cognitive/think`
- 读取接口：`GET /cognitive/sessions`、`GET /cognitive/sessions/{session_id}/state`、`POST /cognitive/think`
- 是否仍在使用：是，当前主入口使用。

### cognitive_entities

- 用途：保存认知会话中的实体和关系。
- 写入接口：`POST /cognitive/think`
- 读取接口：`GET /cognitive/sessions/{session_id}/state`、`POST /cognitive/think`
- 是否仍在使用：是，当前主入口使用。

### cognitive_messages

- 用途：保存认知流消息。
- 写入接口：`POST /cognitive/think`
- 读取接口：`GET /cognitive/sessions/{session_id}/state`、`POST /cognitive/think`
- 是否仍在使用：是，当前主入口使用。

### cognitive_judgments

- 用途：保存 judgment evolution。
- 写入接口：`POST /cognitive/think`
- 读取接口：`GET /cognitive/sessions/{session_id}/state`、`POST /cognitive/think`
- 是否仍在使用：是，当前主入口使用。

### 重点检查表

| 表名 | 是否存在 | 结论 |
|---|---:|---|
| `agent_runs` | 否 | 规划里提过，但当前 schema 和实际 DB 都没有。 |
| `internal_role_runs` | 是 | 仍在使用。 |
| `research_objects` | 是 | 仍在使用。 |
| `research_sources` | 是 | 仍在使用。 |
| `research_facts` | 是 | 仍在使用。 |
| `conversations` | 否 | Phase 9.3 对话层规划过，但当前没有落表。 |
| `conversation_messages` | 否 | Phase 9.3 对话层规划过，但当前没有落表。 |
| `external_agent_runs` | 是 | 后端可用，前端隐藏。 |

## 4. 当前前端入口清单

当前前端只有一个页面：

```text
frontend/app/page.tsx
```

当前页面是 Cognitive Flow 工作台。

### 当前前端调用的 API

| 前端区域 | 调用 API | 说明 |
|---|---|---|
| 最近思维流 | `GET /cognitive/sessions?limit=10` | 页面加载时读取最近 cognitive sessions |
| 自由输入框 | `POST /cognitive/think` | 当前主交互入口 |
| 打开历史 session | `GET /cognitive/sessions/{session_id}/state` | 读取历史认知状态 |

### 当前前端显示的区域

- 当前主题
- 当前实体
- 最近思维流
- 连续思考流
- 自由输入框
- 允许联网补证据开关
- 读取重点来源正文开关
- 当前判断
- 当前证据
- 未解决问题
- 风险
- 下一问
- 研究状态计数
- 已读取文件
- 高级结构化输出折叠区

### 旧功能入口状态

| 功能入口 | 当前前端是否还在 | 结论 |
|---|---:|---|
| Sync Repo 按钮 | 否 | 后端 `/repo/sync` 仍在，前端隐藏。 |
| Rebuild Index 按钮 | 否 | 后端 `/index/rebuild` 仍在，前端隐藏。 |
| Status Audit 按钮 | 否 | 后端 `/agents/status-audit` 仍在，前端隐藏。 |
| 文件浏览页 | 否 | 后端 `/repo/files`、`/repo/file` 仍在，前端隐藏。 |
| 搜索页 | 否 | 后端 `/search`、`/ask` 仍在，前端隐藏。 |
| Internal Roles 页面 | 否 | 后端 `/roles/*` 仍在，前端隐藏。 |
| Research State 页面 | 否 | 后端 `/research/*` 仍在，但没有前端页面。 |
| Patch Draft 页面 | 否 | 后端 `/patch/draft` 仍在，前端隐藏。 |
| Graph 页面 | 否 | 后端 `/graph/*` 仍在，前端隐藏。 |
| Memory 页面 | 否 | 后端 `/memory/*` 仍在，前端隐藏。 |
| Cognitive Flow 页面 | 是 | 覆盖了首页。 |

## 5. 原有核心能力是否还在

| 核心能力 | 是否还在 | 前端是否可见 | 结论 |
|---|---:|---:|---|
| Sync Repo / repo sync | 是 | 否 | 后端仍在，入口隐藏。 |
| Rebuild Index | 是 | 否 | 后端仍在，入口隐藏。 |
| Status Audit | 是 | 否 | 后端仍在，入口隐藏。 |
| `/ask` | 是 | 否 | 后端仍在，入口隐藏。 |
| `/roles/run` | 是 | 否 | 后端仍在，Cognitive Flow 可间接调用 operator。 |
| `/web/search` | 是 | 否 | 后端仍在，前端不直接调用。 |
| `/web/read-source` | 是 | 否 | 后端仍在，前端不直接调用。 |
| `/research/*` | 是 | 否 | 后端仍在，Cognitive Flow 内部使用。 |
| `/cognitive/*` | 是 | 是 | 当前主入口。 |
| `/patch/draft` | 是 | 否 | 后端仍在，入口隐藏。 |
| `/graph/*` | 是 | 否 | 后端仍在，入口隐藏。 |

## 6. 被隐藏或疑似废弃的功能

### 被隐藏但后端仍可用

- 文件浏览：`/repo/files`、`/repo/file`
- 手动同步 SK 仓库：`/repo/sync`
- 重建索引：`/index/rebuild`
- 索引状态：`/index/status`
- 检索：`/search`
- 仓库问答：`/ask`
- 状态审计：`/agents/status-audit`
- 专用 Agent：`/agents/product-teardown`、`/agents/framework-red-team`、`/agents/article-publish-check`
- 入库稿：`/patch/draft`
- 图谱：`/graph/*`
- Memory：`/memory/*`
- Internal Roles：`/roles/*`
- SKGPT 指令读取：`/skgpt/*`
- Research State 管理：`/research/*`
- LLM 调试：`/llm/*`

### 疑似未完成 / 未落地

- `agent_runs` 表不存在。
- `conversations` 表不存在。
- `conversation_messages` 表不存在。
- 独立 intent router 未发现。
- 独立 repo inventory API 未发现。
- Research State 没有独立前端入口。

### 不建议称为废弃

这些模块虽然前端隐藏，但仍被系统能力链需要，不应直接删除：

- `/repo/*`
- `/index/*`
- `/search`
- `/ask`
- `/roles/*`
- `/web/*`
- `/research/*`
- `/patch/draft`
- `/graph/*`

## 7. 当前系统风险

### 风险 1：前端覆盖了原工作台

当前 `frontend/app/page.tsx` 已经变成 Cognitive Flow 单页。

结果：

- 用户看不到 Sync Repo。
- 用户看不到 Rebuild Index。
- 用户看不到 Status Audit。
- 用户看不到 Internal Roles。
- 用户看不到 Patch Draft。
- 用户看不到 Graph。
- 用户看不到 Research State。

这会造成“后端能力还在，但用户以为没了”。

### 风险 2：Cognitive Flow 默认替代所有任务

当前默认首页就是 Cognitive Flow。

它适合连续思考，但不适合所有任务：

- 系统维护
- 同步仓库
- 重建索引
- 状态审计
- 图谱重建
- 入库稿生成
- 查看文件原文

这些任务不应该全部塞进认知流。

### 风险 3：Intent Router 没生效或不存在

未发现独立 intent router。

当前系统没有明确把用户意图路由到：

- repo sync
- index rebuild
- status audit
- patch draft
- graph query
- research state view

Cognitive Flow 目前只是默认思考入口，不是完整任务路由器。

### 风险 4：allow_web 默认没有问题，但用户可能误解

`allow_web` 默认是 `false`，这是正确的安全默认值。

风险在于：

- 前端只显示开关，没有清楚说明“不开就不会联网补证据”。
- 用户可能以为系统已经联网查过。

### 风险 5：Research State 后台化太深

Research State 后端存在，并且 Cognitive Flow 会自动关联。

但前端没有对象页，用户看不到：

- 某个对象有哪些来源
- 哪些来源已读
- 哪些事实只是候选
- 哪些缺口还没补

### 风险 6：Repo Inventory 功能不存在或未接入

未发现 `/inventory`、`/system/inventory`、`/admin/modules` 一类接口。

当前没有一个用户可点的“系统有哪些能力”页面。

## 8. 建议保留 / 暂停 / 恢复的模块

### A. 必须保留

- Repo Reader：`/repo/files`、`/repo/file`、`/repo/canonical`
- Repo Sync：`/repo/sync`
- Index：`/index/rebuild`、`/index/status`、`/index/chunks`
- Search / Ask：`/search`、`/ask`
- Canonical Preflight
- Status Audit：`/agents/status-audit`
- Patch Draft：`/patch/draft`
- Web Search：`/web/search`
- Source Reader：`/web/read-source`
- Internal Roles：`/roles/run`
- Research State：`/research/*`
- Cognitive Flow：`/cognitive/*`
- 核心数据库表：`files`、`chunks`、`index_runs`、`internal_role_runs`、`research_*`、`cognitive_*`

### B. 可选保留

- Graph：`/graph/*`
- Memory registries：`/memory/core`、`/memory/registries`、`/memory/episodes`
- External Agent Runs：`/memory/external-run`、`/memory/external-runs`
- SKGPT 指令读取：`/skgpt/*`
- LLM 调试接口：`/llm/config`、`/llm/chat`

### C. 建议暂停 / 隐藏

- 手动 external run 表单
- 低层 `/llm/chat` 前端入口
- 用户手动 ingest role run
- 用户手动添加 research source
- 复杂图谱查询作为默认入口
- 任何自动 commit / push / PR 能力

## 9. 最小恢复方案

以下只是方案，不执行。

### Step 1：恢复“系统入口导航”

保留 Cognitive Flow 首页，但增加顶部或左侧固定导航：

```text
思维流
仓库
索引
检索
审计
入库稿
图谱
Research State
Internal Roles
系统状态
```

不要恢复成复杂旧首页，只恢复入口。

### Step 2：恢复 4 个运维按钮

在“系统状态”或“仓库”页恢复：

- Sync Repo
- Rebuild Index
- Status Audit
- Graph Status / Rebuild Graph

### Step 3：给 Research State 一个只读页

先只做查看，不做编辑：

- research objects 列表
- sources
- facts
- gaps
- risks
- next_actions

### Step 4：保留 Cognitive Flow 为默认主入口

不要回退 Phase 11。

正确关系应是：

```text
Cognitive Flow = 用户主入口
旧工作台功能 = 工具抽屉 / 运维入口 / 高级模式
Research State = 后台状态层 + 只读查看
Internal Roles = 内部 operator + 高级调试入口
```

### Step 5：补一个轻量 Intent Router

只做显式路由，不做复杂 autonomous agent：

```text
“同步仓库” -> 提示用户去 Sync Repo 按钮
“重建索引” -> 提示用户去 Rebuild Index 按钮
“做状态审计” -> 调用 /agents/status-audit 或提示确认
“生成入库稿” -> 引导 /patch/draft
“查图谱” -> 引导 /graph
普通思考 -> /cognitive/think
```

### Step 6：新增 System Inventory 只读入口

后续可以做一个只读页面：

- 后端 API 是否存在
- 数据库表是否存在
- 当前前端调用了哪些 API
- 哪些模块隐藏

本次报告可作为第一版清单。

### Step 7：不要删除任何后端模块

当前最大问题是“前端不可见”，不是“后端冗余”。

建议先恢复可见性，再决定是否废弃。
