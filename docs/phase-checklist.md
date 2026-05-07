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
