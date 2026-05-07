# Architecture

## 当前阶段原则

第 0/1 期只做仓库现读底座。系统不推理仓库状态，不生成入库补丁，不自动写 GitHub。

所有后续 Agent 回答都应遵守：

1. 先读取 SK 仓库当前文件。
2. 明确列出本次读取文件。
3. 再输出判断、风险和入库稿。
4. 找不到材料时不编造。

## 后端

入口：`backend/app/main.py`

模块：

- `config.py`：环境变量和 canonical 文件列表
- `api/repo.py`：仓库读取 API
- `services/repo_reader.py`：仓库读取底座

读取优先级：

1. `LOCAL_REPO_PATH`
2. `GITHUB_RAW_BASE_URL`
3. `GITHUB_REPO` + `GITHUB_BRANCH`

本地读取会做仓库相对路径归一化，并阻止 `..` 越界路径。

Docker Compose 运行时，宿主机 SK 仓库通过 `SK_REPO_PATH` 只读挂载到后端容器：

```text
宿主机：SK_REPO_PATH
容器内：/sk-repo
后端环境变量：LOCAL_REPO_PATH=/sk-repo
```

## API

```text
GET /health
GET /repo/files
GET /repo/file?path=
GET /repo/canonical
POST /index/rebuild
GET /index/status
GET /index/chunks?file_path=
GET /llm/config
POST /llm/chat
POST /search
POST /ask
POST /agents/status-audit
```

## 前端

入口：`frontend/app/page.tsx`

当前首页显示：

- 后端健康状态
- canonical 文件读取数量
- canonical 文件逐项状态
- 文件来源、大小和更新时间

容器运行时，前端服务端渲染使用 `INTERNAL_API_BASE_URL=http://backend:8000` 访问后端，页面展示给浏览器的 API 地址仍是 `http://localhost:8000`。

## Markdown 索引

第 2 期已添加：

- `markdown_parser.py`
- `indexer.py`
- PostgreSQL/pgvector Docker 服务
- PostgreSQL 表：`files`、`chunks`、`index_runs`
- `/index/rebuild`
- `/index/status`
- `/index/chunks?file_path=`

当前切块策略：按 ATX 标题层级切块，忽略代码块中的标题样式文本，记录 `file_path`、`heading`、`content`、`start_line`、`end_line`、`chunk_type`。

## LLM Provider

默认 provider：MiniMax 国内版。

配置：

```text
LLM_PROVIDER=minimax
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_CHAT_ENDPOINT=/chat/completions
MINIMAX_CHAT_MODEL=MiniMax-M2.7
```

`/llm/config` 只返回是否配置 key，不返回 key 本身。`/llm/chat` 是第 3 期前的最小联调接口，后续 `/ask` 会复用同一个 MiniMax client。

## 状态审计

第 4 期已添加：

- `status_auditor.py`
- `/agents/status-audit`

状态审计是规则版，不调用 LLM。它固定读取 canonical 文件，抽取文章编号、发布状态、案例卡字段，并输出最小修复建议。

当前检查：

- README 与执行状态总表是否冲突
- case-index 与 case-cards 是否冲突
- 已发布文章是否仍标待发布
- 案例卡是否缺 `depth_draft`
- 案例卡是否缺 `article_published`

第 3 期再添加：

- `retriever.py`
- 关键词检索
- `/search`
- `/ask`

第 3 期当前已完成关键词检索和最小 `/ask`。pgvector 语义检索待 MiniMax embedding 配置确认后接入。

第 4 期再添加：

- `status_auditor.py`
- `/agents/status-audit`

第 5 期再添加：

- `patch_writer.py`
- `/patch/draft`
