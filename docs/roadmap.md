# Roadmap

## 第 0 期：项目骨架

目标：后端、前端、文档和启动链路可跑。

状态：已完成。

交付：

- FastAPI 后端
- `/health`
- Next.js 前端首页
- README 与基础 docs

## 第 1 期：仓库现读底座

目标：稳定读取 SK 仓库当前文件。

状态：已完成基础版本。

交付：

- `backend/app/services/repo_reader.py`
- `LOCAL_REPO_PATH` 本地读取
- GitHub raw/API 读取预留
- `/repo/files`
- `/repo/file?path=`
- `/repo/canonical`
- canonical 文件固定列表
- 未读取到文件时不判断文件不存在

## 第 2 期：Markdown 解析与索引

目标：按标题层级切块，写入 PostgreSQL。

状态：已完成。

交付：

- `backend/app/services/markdown_parser.py`
- `backend/app/services/indexer.py`
- PostgreSQL/pgvector Docker 服务
- 表：`files`、`chunks`、`index_runs`
- `POST /index/rebuild`
- `GET /index/status`
- `GET /index/chunks?file_path=`
- GitHub SK 仓库索引重建成功：170 个 Markdown 文件，3703 个 chunk

## 第 3 期：基础检索问答

目标：关键词、pgvector、混合检索与基础问答。

状态：无 embedding 可用版已完成；pgvector 语义检索待 MiniMax embedding 信息确认。

已完成：

- `backend/app/services/retriever.py`
- 关键词检索
- 中文问题轻量切词
- SK 领域同义词：`格式 -> format`、`案例卡 <-> case-card`
- 文件路径命中优先召回
- 单文件结果多样性控制
- `POST /search`
- `backend/app/services/qa_service.py`
- MiniMax 最小问答
- `POST /ask`

待完成：

- MiniMax embedding 配置确认
- pgvector 语义检索
- 混合检索：keyword score + vector score + file priority score

## 第 4 期：状态校准 Agent

目标：检查 README、执行状态总表、case-index、case-cards 之间的状态漂移。

状态：规则版已完成。

交付：

- `backend/app/services/status_auditor.py`
- `POST /agents/status-audit`
- 固定读取 canonical 文件
- 输出结论、已读取文件、冲突、风险等级、最小修复方案、建议修改文件、Codex 执行指令

真实 SK 仓库验证：

- canonical 读取：4/4
- 容器内测试：19 passed
- 本次审计结果：`risk=high conflict_count=8`

## 第 5 期：GitHub 入库稿生成器

目标：生成可审核入库稿、diff 说明、commit message、PR 文案。

状态：未开始。

## 第 6 期：SK 专用 Agent

目标：产品轻量初拆、框架红队、文章发布检查。

状态：未开始。

## 第 7 期：前端工作台

目标：文件浏览、检索、状态审计、Agent 运行、入库稿查看。

状态：未开始。

## 第 8 期：图数据库

目标：在前面阶段跑通后再接入 Neo4j。

状态：未开始。
