# Phase Checklist

## 第 0 期：项目骨架

状态：完成。

- [x] 创建 `sk-agent` 项目目录
- [x] 初始化 `backend` FastAPI
- [x] 初始化 `frontend` Next.js
- [x] 添加 `.env.example`
- [x] 添加 `README.md`
- [x] 添加 `docs/roadmap.md`
- [x] 添加 `docs/architecture.md`
- [x] 添加 Docker Compose 运行方式
- [x] 后端提供 `/health`
- [x] 前端首页显示 “SK Agent 工作台”

验收：

- [x] `/health` 实现为 `{"status": "ok"}`
- [x] 前端首页实现
- [x] README 说明启动方式
- [x] Docker 后端镜像构建通过
- [x] Docker 前端镜像构建通过
- [x] 容器内后端测试通过
- [x] 容器内前端构建通过
- [x] `http://localhost:8000/health` 返回 ok
- [x] `http://localhost:3000` 返回 200
- [x] 默认空仓库挂载下 `/repo/canonical` 返回 `partial read_count=0 total=4`
- [x] 前端依赖已生成 `package-lock.json`，Docker 构建使用 `npm ci`

## 第 1 期：仓库现读底座

状态：完成基础版本。

- [x] 实现 `backend/app/services/repo_reader.py`
- [x] 支持 `LOCAL_REPO_PATH` 本地读取
- [x] `LOCAL_REPO_PATH` 已配置但不可读时返回明确错误
- [x] 预留 GitHub raw URL 读取
- [x] 预留 GitHub API 读取
- [x] 支持读取单个文件
- [x] 支持列出仓库文件树
- [x] 返回文件元信息：`path`、`size`、`last_modified`、`source`
- [x] API：`GET /repo/files`
- [x] API：`GET /repo/file?path=`
- [x] API：`GET /repo/canonical`
- [x] canonical 文件固定为 4 个指定路径
- [x] 未读取到文件时返回 `status: not_found`
- [x] 未读取到文件时不判断文件不存在

验收：

- [x] 代码路径已支持读取 `README.md`
- [x] 代码路径已支持读取 `ops/执行状态总表.md`
- [x] 代码路径已支持读取 `cases/2026/case-index.md`
- [x] 代码路径已支持读取 `cases/2026/case-cards.md`
- [x] 缺失文件返回“本次未读取到，文件未读取到不等于文件不存在”

真实 SK 仓库联调：

- [x] 设置 GitHub 仓库：`MRYGP/SK`
- [x] 设置 GitHub 分支：`main`
- [x] 设置 GitHub raw 地址：`https://raw.githubusercontent.com/MRYGP/SK/main`
- [x] GitHub 模式下设置 `LOCAL_REPO_PATH` 为空，避免空本地挂载抢占读取
- [x] 启动后端
- [x] 调用 `/repo/canonical`
- [x] 确认 4 个 canonical 文件均读取成功：`status=ok read_count=4 total=4`
- [x] 调用 `/repo/files`：`status=ok source=github_api count=175`

## 第 2 期：Markdown 解析与索引

状态：完成。

- [x] 实现 `backend/app/services/markdown_parser.py`
- [x] 按标题层级切块
- [x] 忽略代码块中的伪标题
- [x] chunk 保存字段：`file_path`
- [x] chunk 保存字段：`heading`
- [x] chunk 保存字段：`content`
- [x] chunk 保存字段：`start_line`
- [x] chunk 保存字段：`end_line`
- [x] chunk 保存字段：`chunk_type`
- [x] PostgreSQL 建表：`files`
- [x] PostgreSQL 建表：`chunks`
- [x] PostgreSQL 建表：`index_runs`
- [x] Docker Compose 增加 PostgreSQL/pgvector 服务
- [x] 支持重建索引
- [x] API：`POST /index/rebuild`
- [x] API：`GET /index/status`
- [x] API：`GET /index/chunks?file_path=`

验收：

- [x] 容器内后端测试通过：7 passed
- [x] `/index/status` 可返回文件数与 chunk 数
- [x] `/index/rebuild` 执行成功
- [x] SK GitHub 仓库索引结果：`total_files=170 indexed_files=170 chunk_count=3703`
- [x] 可按文件路径查看 chunk：`README.md count=21`

## 当前暂不实现

- [ ] pgvector 检索
- [ ] 状态校准 Agent
- [ ] 入库稿生成器
- [ ] 专用 Agent 工作流
- [ ] Neo4j 图数据库

## MiniMax 国内版适配

状态：完成基础配置。

- [x] 环境变量增加 `LLM_PROVIDER=minimax`
- [x] 环境变量增加 `MINIMAX_API_KEY`
- [x] 环境变量增加 `MINIMAX_BASE_URL`
- [x] 环境变量增加 `MINIMAX_CHAT_ENDPOINT`
- [x] 环境变量增加 `MINIMAX_CHAT_MODEL`
- [x] Docker Compose 将 MiniMax 配置注入 backend
- [x] 新增 `backend/app/services/llm_client.py`
- [x] 新增 `GET /llm/config`
- [x] 新增 `POST /llm/chat`
- [x] MiniMax key 不在接口中回显

## 第 3 期：基础检索问答

状态：无 embedding 可用版完成。

- [x] 实现 `backend/app/services/retriever.py`
- [x] 实现关键词检索
- [x] 实现中文问题轻量切词
- [x] 实现 SK 领域同义词映射
- [x] 实现路径命中文件优先召回
- [x] 实现单文件结果多样性控制
- [x] 实现文件优先级分
- [x] API：`POST /search`
- [x] 实现 `backend/app/services/qa_service.py`
- [x] API：`POST /ask`
- [x] `/ask` 回答前会基于检索结果重新读取命中文件元信息
- [x] `/ask` 返回已读取文件
- [x] `/ask` 返回引用路径和行号
- [x] MiniMax reasoning 内容不回显，只返回 `reasoning_present`
- [ ] MiniMax embedding 配置确认
- [ ] pgvector 语义检索
- [ ] 混合检索：`keyword score` + `vector score` + `file priority score`

验收：

- [x] 容器内后端测试通过：15 passed
- [x] `/search` 可检索 `MTP 构思招募法在哪`
- [x] `/search` 可检索 `诊断空白四条件是什么`
- [x] `/search` 可检索 `case-card 格式在哪里`
- [x] `/search` 可检索 `产品评估决策清单有哪些必须条件`
- [x] `/ask` 可调用 MiniMax 并返回引用

## 第 5 期：GitHub 入库稿生成器

状态：完成本地草稿版。

- [x] 新增 `backend/app/services/patch_writer.py`
- [x] 输入支持目标文件、修改意图、新增内容
- [x] 支持 `auto`、`create`、`append`、`replace` 草稿模式
- [x] 输出建议保存路径
- [x] 输出 Markdown 正文
- [x] 输出 diff 说明和 diff preview
- [x] 输出 commit message
- [x] 输出 PR title
- [x] 输出 PR body
- [x] API：`POST /patch/draft`
- [x] 草稿生成前先读取目标文件
- [x] 目标文件未读取到时只提示“本次未读取到”，不判断文件不存在
- [x] 不写本地 SK 仓库
- [x] 不调用 GitHub 写入 API

验收：

- [x] 后端 Docker 测试通过：`22 passed`
- [x] 可生成新增轻量初拆文档草稿
- [x] 可生成更新执行状态总表草稿
- [x] 可生成更新 case-cards 草稿
- [x] 可生成写入清单草稿

## 第 6 期：SK 专用 Agent

状态：完成后端第一版。

- [x] Agent 1：产品轻量初拆
- [x] 产品轻量初拆会先运行状态校准
- [x] 产品轻量初拆会搜索仓库是否已有相关内容
- [x] 产品轻量初拆会读取轻量初拆模板候选文件
- [x] 产品轻量初拆会输出是否建议入库或先排重
- [x] Agent 2：框架红队
- [x] 框架红队会读取项目审问清单候选文件
- [x] 框架红队会读取产品评估决策清单候选文件
- [x] 框架红队会读取 `core/failure_modes.yml`
- [x] 框架红队会输出反向排雷和 Kill / Go / Hold 判断
- [x] Agent 3：文章发布检查
- [x] 文章发布检查会读取公众号写作指南候选文件
- [x] 文章发布检查会读取内容生产经验手册候选文件
- [x] 文章发布检查会读取发布 SOP 候选文件
- [x] 文章发布检查会输出风险检查和发布包
- [x] API：`POST /agents/product-teardown`
- [x] API：`POST /agents/framework-red-team`
- [x] API：`POST /agents/article-publish-check`
- [x] MiniMax 不可用时返回规则版骨架，不阻塞流程
- [x] 不写本地 SK 仓库
- [x] 不调用 GitHub 写入 API

验收：

- [x] 后端 Docker 测试通过：`26 passed`

## 第 7 期：前端工作台

状态：完成第一版可用工作台。

- [x] 首页：当前仓库状态
- [x] 文件页：浏览 SK 文件
- [x] 检索页：搜索知识库
- [x] 检索页：运行 `/ask`
- [x] 状态审计页：显示漂移结果
- [x] Agent 页：运行 SK 专用 Agent
- [x] 入库稿页：查看 patch 草稿
- [x] 前端能读取 canonical 文件
- [x] 前端能运行状态审计
- [x] 前端能搜索 MTP / 诊断空白 / failure_modes
- [x] 前端能查看入库稿
- [x] 不写本地 SK 仓库
- [x] 不调用 GitHub 写入 API

验收：

- [x] 前端 Docker 构建通过
- [x] `docker compose run --rm frontend npm run build` 通过
- [x] `http://localhost:3000` 返回 200

## 第 8 期：图数据库

状态：完成 Neo4j 第一版。

- [x] Docker Compose 增加 Neo4j 5 Community
- [x] 后端增加 Neo4j driver
- [x] `.env.example` 增加 Neo4j 配置
- [x] 实现 `backend/app/services/graph_builder.py`
- [x] 从 PostgreSQL chunks 重建图谱
- [x] 节点：`Product`
- [x] 节点：`Case`
- [x] 节点：`Article`
- [x] 节点：`Framework`
- [x] 节点：`FailureMode`
- [x] 节点：`Theory`
- [x] 节点：`File`
- [x] 节点：`Decision`
- [x] 节点：`Signal`
- [x] 关系：`APPEARS_IN`
- [x] 关系：`TRIGGERS`
- [x] 关系：`USES`
- [x] 关系：`REFERENCES`
- [x] 关系：`HAS_DECISION`
- [x] API：`POST /graph/rebuild`
- [x] API：`GET /graph/status`
- [x] API：`GET /graph/failure-modes/{code}/cases`
- [x] API：`GET /graph/frameworks/articles?framework=`
- [x] API：`GET /graph/products/tools`
- [x] API：`GET /graph/theories/reused`

验收：

- [x] 后端单元测试通过：`28 passed`
- [x] `/graph/rebuild` 成功：`source_chunk_count=3703 node_count=535 relationship_count=1358`
- [x] `/graph/status` 成功
- [x] 可查询：哪些案例命中 FM015
- [x] 可查询：诊断空白框架出现在哪些文章
- [x] 可查询：哪些产品被判为“工具”
- [x] 可查询：哪些理论被多个案例引用

## 第 8.5 期：规约收口与双仓边界

状态：完成。

- [x] 新增统一 `canonical_preflight()`
- [x] `/ask` 接入 canonical preflight
- [x] `/agents/status-audit` 接入 canonical preflight
- [x] `/agents/product-teardown` 接入 canonical preflight
- [x] `/agents/framework-red-team` 接入 canonical preflight
- [x] `/agents/article-publish-check` 接入 canonical preflight
- [x] Agent 输出包含 `conclusion`
- [x] Agent 输出包含 `read_files`
- [x] Agent 输出包含 `evidence`
- [x] Agent 输出包含 `risks`
- [x] Agent 输出包含 `minimal_next_step`
- [x] Agent 输出包含 `ingest_draft`
- [x] Agent 输出包含 `answer_markdown`
- [x] `.env.example` 增加 SK / SKGPT 双仓变量
- [x] 文档说明 SK / SKGPT 双仓边界
- [x] SKGPT 配置目录不进入 SK 内容索引
- [x] `/graph/status` 增加图谱新鲜度字段
- [x] 文档注明 Graph is advisory only
- [x] 前端保存最近 10 次 Agent 执行记录
- [x] 不实现自动 commit
- [x] 不实现自动 PR
- [x] 不新增 Agent
- [x] 不修改 SK 仓库内容

验收：
- [x] 后端 Docker 测试通过：`33 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`
- [x] 输出 `docs/phase-8-5-compliance.md`

## 第 9.2 期：多智能体记忆与路由系统

状态：完成第一版；外部记录能力保留为外援记录。

- [x] 新增 `memory/core_memory.md`
- [x] 新增 `memory/constitution.md`
- [x] 新增 `memory/agent_registry.md`
- [x] 新增 `memory/gpts_registry.md`
- [x] 新增 `memory/external_tools.md`
- [x] 新增 `memory/episodes/drift-log.md`
- [x] 新增 `memory/episodes/agent-lessons.md`
- [x] 新增 `memory/episodes/routing-lessons.md`
- [x] 新增 `external_agent_runs` 表
- [x] 新增 `GET /memory/core`
- [x] 新增 `GET /memory/registries`
- [x] 新增 `GET /memory/episodes`
- [x] 新增 `POST /memory/external-run`
- [x] 新增 `GET /memory/external-runs?limit=20`
- [x] 前端新增最小 Memory 入口
- [x] `memory/` 不进入 SK 内容索引
- [x] 不引入 Vue / LangGraph / Mem0 / Zep / Letta
- [x] 不自动 commit / PR / 写 SK 仓库

验收：
- [x] 后端 Docker 测试通过：`38 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`
- [x] 输出 `docs/phase-9-2-multi-agent-memory.md`

## 第 9.2 修正版：内部多角色记忆与路由系统

状态：完成。

- [x] 新增 `backend/app/roles/base_role.py`
- [x] 新增 `backend/app/roles/role_registry.py`
- [x] 新增 `backend/app/roles/role_router.py`
- [x] 新增 `deep_researcher_role`
- [x] 新增 `writing_workshop_role`
- [x] 新增 `first_reader_role`
- [x] 新增 `product_teardown_role`
- [x] 新增 `repo_governance_role`
- [x] 新增 `patch_writer_role`
- [x] 新增 `internal_role_runs` 表
- [x] 新增 `GET /roles`
- [x] 新增 `POST /roles/run`
- [x] 新增 `GET /roles/runs?limit=10`
- [x] `/roles/run` 统一 canonical preflight
- [x] `/roles/run` 写入 `internal_role_runs`
- [x] 新增 `memory/internal_roles.md`
- [x] 新增 `memory/episodes/role-lessons.md`
- [x] 新增 `docs/internal-role-system.md`
- [x] 新增 `docs/phase-9-2-internal-role-memory.md`
- [x] 前端 Memory 页调整为内部角色主入口
- [x] 不引入 Vue / LangGraph / Mem0 / Zep / Letta
- [x] 不自动 commit / push / PR / 写 SK 仓库

验收：
- [x] 后端 Docker 测试通过：`45 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`
- [x] `/roles/run` 实际调用成功

## 第 9.4 期：连接 SKGPT 角色指令仓库

状态：完成第一版。

- [x] `.env.example` 增加 `SKGPT_REPO_URL=https://github.com/MRYGP/SKGPT.git`
- [x] `.env.example` 增加 `SKGPT_BRANCH=main`
- [x] Docker backend 增加 SKGPT 读取配置
- [x] 新增 `backend/app/services/skgpt_reader.py`
- [x] 新增 `backend/app/roles/role_prompt_loader.py`
- [x] 新增 `backend/app/api/skgpt.py`
- [x] 新增 `memory/role_prompt_mapping.yml`
- [x] 新增 `GET /skgpt/files`
- [x] 新增 `GET /skgpt/file?path=`
- [x] 新增 `GET /skgpt/role-prompts`
- [x] `/skgpt/role-prompts` 可读取 SKGPT 中已存在的角色指令文件
- [x] SKGPT 只作为角色配置源，不进入 SK 内容索引
- [x] 不自动 commit / push / PR / 写 SK 仓库

验收：
- [x] 后端 Docker 测试通过：`49 passed`
- [x] 已重启 backend 容器
- [x] `/skgpt/role-prompts` 实际调用成功
- [x] 输出 `docs/phase-9-4-skgpt-role-prompts.md`

## 第 9.3 期：内部角色可控联网

状态：完成第一版。

- [x] 新增 `backend/app/services/web_search.py`
- [x] 新增 `backend/app/services/search_providers/base.py`
- [x] 新增 `backend/app/services/search_providers/mock_provider.py`
- [x] 新增 `backend/app/services/search_providers/tavily_provider.py`
- [x] 新增 `backend/app/services/evidence_classifier.py`
- [x] 新增 `POST /web/search`
- [x] `/roles/run` 增加 `allow_web` 和 `web_queries`
- [x] `deep_researcher_role` 接入候选联网证据
- [x] `product_teardown_role` 接入候选联网证据
- [x] 新增 `article_publish_check_role`
- [x] 不允许联网的 role 返回 warning，不执行联网
- [x] 前端内部角色页增加“允许联网补证据”
- [x] 前端内部角色页增加 `web_queries` 输入框
- [x] 输出 `docs/phase-9-3-controlled-web-search.md`

验收：
- [x] 后端 Docker 测试通过：`56 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`

## 第 9.3a 期：Human Readable Research View

状态：完成第一版。

- [x] 保留 `structured_output`
- [x] `/roles/run` 新增 `human_readable_markdown`
- [x] 前端默认显示人类可读研究简报
- [x] 前端默认显示结论、候选来源、缺失证据、风险、下一步
- [x] 结构化 JSON 折叠到“查看结构化输出”
- [x] 不修改角色业务逻辑
- [x] 不移除 `structured_output`

验收：
- [x] 后端 Docker 测试通过：`56 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`

## 第 9.3b 期：接入真实 Tavily 搜索

状态：完成第一版，等待用户填写 `TAVILY_API_KEY`。

- [x] `tavily_provider.py` 使用 Tavily Search API
- [x] 使用 `TAVILY_API_KEY`
- [x] `/web/search` 可返回 `provider=tavily`
- [x] 保留 `title/url/snippet/fetched_at/provider`
- [x] 保留 `source_type` 分类
- [x] 保留 evidence candidate 规则
- [x] Tavily 搜索失败自动 fallback 到 `mock_provider`
- [x] 新增 `docs/phase-9-3b-tavily.md`
- [x] 不修改角色系统
- [x] 不修改 canonical preflight
- [x] 不自动入库

验收：
- [x] 后端 Docker 测试通过：`58 passed`

## 第 9.3c 期：Search Query Expansion

状态：完成第一版。

- [x] 新增 `backend/app/services/query_expander.py`
- [x] `deep_researcher_role` 默认扩展 Hippocratic AI / startup / healthcare / founder / funding
- [x] `product_teardown_role` 默认扩展 pricing / revenue / funding / competitors / reviews reddit
- [x] `article_publish_check_role` 默认扩展 latest / official / announcement
- [x] 显式 `web_queries` 优先，不自动扩展
- [x] `/roles/run` 新增 `expanded_queries`
- [x] 前端显示“实际搜索词”
- [x] 新增 `docs/phase-9-3c-query-expansion.md`

验收：
- [x] 后端 Docker 测试通过：`63 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`

## 第 9.3d 期：Source Type Classifier 优化

状态：完成第一版。

- [x] 新增 `backend/app/services/source_classifier.py`
- [x] 支持 `official`
- [x] 支持 `app_store`
- [x] 支持 `company_profile`
- [x] 支持 `media`
- [x] 支持 `community`
- [x] 支持 `unknown`
- [x] 搜索结果新增 `source_reason`
- [x] evidence candidate 规则扩展到 app store / company profile / announcement wire
- [x] deep_research_role 根据已有来源调整缺失证据
- [x] 前端候选来源显示 source_type / evidence_level / source_reason / url
- [x] 新增 `docs/phase-9-3d-source-classifier.md`

验收：
- [x] 后端 Docker 测试通过：`68 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`

## 第 9.3e 期：Conversation Context Carryover

状态：完成第一版。

- [x] 新增 `backend/app/services/conversation_intent.py`
- [x] `/roles/run` 增加 `conversation_id`
- [x] 识别“基于以上 / 继续 / 刚才”等承接型指令
- [x] 承接型指令不自动生成新 web query
- [x] 承接型指令不自动调用 web_search
- [x] 可继承上一轮 `internal_role_runs.structured_output`
- [x] deep_research_role 可基于上一轮 evidence_ledger 输出整理报告
- [x] 输出 `context_used / carryover_intent / inherited_sources_count / new_web_search_performed`
- [x] 前端显示上下文继承状态
- [x] 新增 `docs/phase-9-3e-conversation-carryover.md`

验收：
- [x] 后端 Docker 测试通过：`71 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`

## 第 9.4 期：Source Reader 来源正文读取

状态：完成第一版。

- [x] 新增 `backend/app/services/source_reader.py`
- [x] 新增 `POST /web/read-source`
- [x] 支持 `official`
- [x] 支持 `app_store`
- [x] 支持 `company_profile`
- [x] 支持 `media`
- [x] deep_research_role 支持 `read_sources`
- [x] 输出 `source_reading_used / read_sources_count`
- [x] 输出 `extracted_facts / candidate_claims / source_quotes`
- [x] 前端候选来源增加“读取正文”按钮
- [x] 新增 `docs/phase-9-4-source-reader.md`
- [x] 不自动入库 / 不自动写案例卡 / 不自动 commit / PR

验收：
- [x] 后端 Docker 测试通过：`75 passed`
- [x] 前端 Docker 构建通过：`docker compose run --rm frontend npm run build`
