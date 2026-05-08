# Phase 8 后验收审计报告

## 1. 总结论

轻微偏移。

当前 `sk-agent` 没有偏离到“自动写仓库”或“图数据库替代 canonical files”的危险方向，核心仍然是本地优先读取 SK 仓库、索引、审计、生成草稿和前端工作台。

但存在 3 个必须收口的偏移风险：

1. “每次任务都先读取 canonical files”没有被全局强制执行。
2. `MRYGP/SK` 与 `MRYGP/SKGPT` 的职责边界没有在配置、代码、前端和文档中显式建模。
3. 部分 Agent 输出依赖 prompt 约束，尚未在后端响应结构中强制包含“结论、风险、最小下一步、入库稿草案”等固定字段。

因此当前适合进入“修正规约层”阶段，不建议继续堆新功能。

## 2. 已检查模块

- 后端入口：`backend/app/main.py`
- 配置：`backend/app/config.py`
- 仓库读取：`backend/app/services/repo_reader.py`
- 仓库同步：`backend/app/services/repo_sync.py`
- 状态审计：`backend/app/services/status_auditor.py`
- 检索问答：`backend/app/services/retriever.py`、`backend/app/services/qa_service.py`
- SK 专用 Agent：`backend/app/services/sk_workflow_agents.py`
- 入库稿生成：`backend/app/services/patch_writer.py`
- 图数据库：`backend/app/services/graph_builder.py`、`backend/app/api/graph.py`
- API 路由：`backend/app/api/*.py`
- 前端工作台：`frontend/app/page.tsx`
- n8n 同步：`n8n/workflows/sk-repo-sync.json`
- Docker 编排：`docker-compose.yml`
- 阶段文档：`README.md`、`docs/phase-*.md`、`docs/beginner-manual.md`

## 3. 符合原规划的部分

### 3.1 仓库读取底座基本符合

当前支持：

- `LOCAL_REPO_PATH`
- GitHub raw/API
- `/repo/files`
- `/repo/file?path=`
- `/repo/canonical`
- canonical 文件固定列表

canonical 文件为：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

`StatusAuditor` 会固定读取 canonical files，并在读取不完整时给出高风险冲突。

### 3.2 自动写仓库风险目前可控

当前没有发现直接向 SK GitHub 仓库执行：

- `git commit`
- `git push`
- GitHub contents write API
- 自动 PR 创建
- 自动修改 SK 仓库文件

`/patch/draft` 只生成：

- 建议路径
- Markdown 正文
- diff preview
- commit message
- PR title
- PR body

这符合“先生成可审核入库稿，不直接改仓库”的规划。

### 3.3 n8n 同步不是写仓库

n8n workflow 调用：

```text
POST /repo/sync
POST /index/rebuild
POST /graph/rebuild
GET /graph/status
```

`/repo/sync` 是从 GitHub zipball 下载最新仓库到本地缓存，不向 GitHub 写入。它属于读取/同步缓存，不属于入库写操作。

### 3.4 图数据库定位基本正确

Neo4j 当前从 PostgreSQL chunks 重建图谱，提供关系查询：

- failure mode -> cases
- framework -> articles
- products -> decisions
- theories -> reused cases

它没有替代 `/repo/canonical`，也没有替代 `status_auditor.py` 的 canonical 读取逻辑。

### 3.5 前端工作台覆盖主要验收面

前端已经有：

- 仓库状态
- canonical 文件状态
- 文件浏览
- 检索与问答
- 状态审计
- 三个 Agent
- 入库稿草案
- 图谱查询
- 手动拉取 SK 仓库按钮

这基本满足第 7 期工作台要求。

## 4. 偏移风险

### 4.1 高优先级：不是所有任务都先读 canonical files

当前只有以下流程明确读取 canonical：

- `/repo/canonical`
- `/agents/status-audit`
- `/agents/product-teardown`，因为它先调用 `StatusAuditor`

以下流程没有先读取 canonical files：

- `/ask`
- `/search`
- `/patch/draft`
- `/agents/framework-red-team`
- `/agents/article-publish-check`
- `/graph/rebuild`
- `/graph/status`
- `/graph/*` 查询
- `/repo/sync`

其中 `/search`、`/repo/sync`、`/graph/status` 可以理解为工具型接口，不一定需要读 canonical。  
但 `/ask` 和两个 Agent 工作流属于“回答/判断型任务”，按原始原则应该先读取 canonical，并把读取结果放入输出。

风险判断：中高。

### 4.2 高优先级：SK 与 SKGPT 未显式区分

当前项目配置只明确了：

```text
REPO_SYNC_URL=https://github.com/MRYGP/SK.git
GITHUB_REPO=MRYGP/SK
```

没有发现以下概念的代码或配置：

- `MRYGP/SKGPT`
- Project Instructions
- GPTS 配置
- 上传清单
- 现读协议

这意味着当前系统没有混写 SKGPT，但也没有显式区分 SK 与 SKGPT。

风险在于后续如果把 GPTS 配置、现读协议、上传清单也塞进 SK 内容仓库读取流，可能污染：

- 内容检索
- 状态审计
- 图谱抽取
- Agent 判断依据

风险判断：中高。

### 4.3 中优先级：Agent 输出格式主要依赖 prompt

`sk_workflow_agents.py` 的 prompt 要求输出：

- 结论
- 已读取文件
- 关键依据
- 风险与不确定性
- 建议入库稿 / 发布包 / 红队结论
- 下一步执行指令

但后端响应结构没有强制拆成固定字段。当前主要返回：

```text
answer
read_files
llm
search
ingest_recommendation
```

这会导致模型偶发漏项时，前端和测试无法稳定发现。

风险判断：中。

### 4.4 中优先级：入库稿没有与 Agent 输出形成强制闭环

产品轻量初拆会输出是否建议入库和建议路径，但不会自动调用 `/patch/draft` 生成结构化入库稿。

这不是自动写风险，但会造成“Agent 说建议入库”和“可审核入库稿”之间存在人工断点。

风险判断：中。

### 4.5 中优先级：图谱抽取依赖 chunks，不主动校验 canonical 新鲜度

`/graph/rebuild` 从 PostgreSQL chunks 读取数据。  
如果用户没有先运行：

```text
/repo/sync
/index/rebuild
```

图谱可能基于旧索引重建。

文档里已有说明，但接口层没有强制检查 latest index run 是否新于 repo sync。

风险判断：中。

### 4.6 低到中优先级：前端没有持久化 Agent 执行记录

前端能显示当前一次 Agent 结果，但没有持久化执行历史。  
如果刷新页面，执行记录会丢失。

这与“前端工作台能显示 Agent 执行记录”的严格要求相比，只满足“当前执行结果显示”，不满足“历史记录显示”。

风险判断：中。

## 5. 必须修复的问题

### 5.1 为回答型任务增加 canonical preflight

必须修复范围：

- `/ask`
- `/agents/framework-red-team`
- `/agents/article-publish-check`
- `/agents/product-teardown` 保持现有状态审计读取，但建议统一入口

建议规则：

```text
回答型任务开始
↓
读取 canonical files
↓
记录 read_files
↓
再执行搜索 / Agent / LLM
↓
输出中合并 canonical read_files 与任务 read_files
```

### 5.2 建立 SK 与 SKGPT 的配置边界

必须新增概念，但不建议马上做复杂功能：

```text
SK_REPO_URL        MRYGP/SK
SKGPT_REPO_URL     MRYGP/SKGPT
SK_CANONICAL       内容、案例、状态、方法论
SKGPT_CANONICAL    Project Instructions、GPTS 配置、上传清单、现读协议
```

最小修复目标：

- 文档明确两个仓库职责
- 配置明确两个仓库变量
- 代码不把 SKGPT 文件混入 SK 内容索引

### 5.3 固化 Agent 输出 schema

建议所有 Agent 响应至少包含：

```text
conclusion
read_files
evidence
risks
minimal_next_step
ingest_draft
answer
```

其中 `answer` 可以保留为 Markdown，结构化字段用于前端和测试验收。

### 5.4 前端增加 Agent 执行记录区

当前前端只显示最近一次结果。  
建议最小修复为本地内存历史，不必先上数据库：

```text
agent_runs: 最近 10 次
字段：时间、agent、输入、read_files、risk、summary
```

### 5.5 图谱页明确显示“来源索引时间”

图谱是辅助层，必须让用户知道它基于哪次索引。

建议图谱状态显示：

```text
latest_index_run
graph_rebuild_time
source_chunk_count
canonical_read_status
```

## 6. 暂不建议继续做的功能

在修复以上问题前，不建议继续做：

1. 自动 GitHub 写入、自动 PR、自动 merge。
2. 让 n8n 自动提交入库稿。
3. 用图谱结果直接驱动 Agent 结论，而不重新读取 canonical files。
4. 增加更多 Agent 类型。
5. 复杂多 Agent 编排或 LangGraph。
6. 把 SKGPT 文件混入 SK 内容知识库。
7. 前端复杂可视化图谱。
8. 自动修复状态漂移并写回仓库。

## 7. 下一阶段建议

建议下一阶段命名为：

```text
Phase 8.5：规约收口与双仓边界
```

优先级如下：

### P0：canonical preflight

给 `/ask` 和所有 Agent 增加统一 canonical preflight。

验收标准：

```text
每个回答型接口 response.read_files 必含 4 个 canonical 文件读取记录。
```

### P0：SK / SKGPT 双仓说明与配置

明确：

```text
SK：内容、案例、状态、方法论
SKGPT：Project Instructions、GPTS 配置、上传清单、现读协议
```

验收标准：

```text
文档、.env.example、配置命名均能区分 SK_REPO 与 SKGPT_REPO。
```

### P1：Agent schema 固化

所有 Agent 输出结构化字段：

```text
conclusion
read_files
risks
minimal_next_step
ingest_draft
```

验收标准：

```text
后端测试能断言这些字段存在。
```

### P1：前端执行记录

前端至少显示最近 10 次 Agent 执行记录。

验收标准：

```text
刷新前页面内可比较多次 Agent 输出。
```

### P2：图谱新鲜度提示

图谱查询页显示图谱来源索引状态。

验收标准：

```text
用户能看到 graph 基于多少 chunks、哪次 index run。
```

最终判断：

> 当前 sk-agent 主方向没有严重偏移，但已经到了必须先固化规约、再继续扩功能的阶段。

