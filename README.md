# SK Agent 工作台

新手先看：

- [SK Agent 工作台保姆级说明书](docs/beginner-manual.md)
- [n8n 自动同步 SK 仓库](docs/n8n-sk-sync.md)

本项目是本地优先的 SK 仓库 Agent 工作台。当前只实现第 0 期和第 1 期，核心验证一句话：

> SK Agent 能稳定读取 SK 仓库当前文件，并明确本次读到了什么。

## 技术栈

- 后端：Python + FastAPI
- 前端：Next.js + TypeScript + Tailwind
- 数据库：PostgreSQL，第 2 期已接入
- 向量检索：pgvector，第 3 期再接入；Docker 已使用 pgvector 镜像
- 图数据库：不在当前阶段实现
- 仓库读取：`LOCAL_REPO_PATH` 优先，GitHub raw/API 预留

## 目录

```text
sk-agent/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ services/repo_reader.py
│  │  └─ api/repo.py
│  ├─ tests/
│  └─ requirements.txt
├─ frontend/
│  ├─ app/
│  ├─ components/
│  ├─ lib/
│  └─ package.json
├─ data/repo_cache/
├─ docs/
└─ .env.example
```

## 环境变量

复制 `.env.example` 后按本机情况配置。第 1 期推荐只用本地仓库路径：

```powershell
$env:LOCAL_REPO_PATH="D:\path\to\your\sk-repo"
```

如果使用 Docker Compose，只需要配置宿主机 SK 仓库路径：

```text
SK_REPO_PATH=D:/path/to/your/sk-repo
```

如果 Docker Hub 拉取慢或不可访问，可以把基础镜像改成你本机可用的镜像源：

```text
PYTHON_IMAGE=python:3.12-slim
NODE_IMAGE=node:20-alpine
```

当前 GitHub 联调配置示例：

```text
LOCAL_REPO_PATH=
GITHUB_REPO=MRYGP/SK
GITHUB_BRANCH=main
GITHUB_RAW_BASE_URL=https://raw.githubusercontent.com/MRYGP/SK/main
```

这个模式下，`/repo/files` 使用 GitHub API 列文件树，`/repo/file` 和 `/repo/canonical` 优先使用 GitHub raw 读取正文。

## MiniMax 国内版模型配置

第 3 期开始使用 MiniMax 作为默认 LLM provider。真实 key 只放 `.env`，不要写入 README 或提交到 Git：

```text
LLM_PROVIDER=minimax
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_CHAT_ENDPOINT=/chat/completions
MINIMAX_CHAT_MODEL=MiniMax-M2.7
MINIMAX_TEMPERATURE=0.2
```

如果你的 MiniMax 控制台给的是其他国内 endpoint，比如 `https://api.minimaxi.com/v1`，只改 `.env` 的 `MINIMAX_BASE_URL`，代码不用动。

检查配置是否进容器：

```powershell
Invoke-RestMethod http://localhost:8000/llm/config
```

填入 `MINIMAX_API_KEY` 后，可用最小聊天接口联调：

```powershell
$body = @{
  messages = @(@{ role = "user"; content = "用一句话介绍你自己" })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post http://localhost:8000/llm/chat -ContentType "application/json" -Body $body
```

Compose 会把这个目录只读挂载到后端容器的 `/sk-repo`，后端容器内固定使用：

```text
LOCAL_REPO_PATH=/sk-repo
```

canonical 文件固定为：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

如果文件本次未读取到，API 返回 `status: not_found`，并提示“本次未读取到，文件未读取到不等于文件不存在”。

## 启动后端

推荐使用 Docker：

```powershell
cd sk-agent
Copy-Item .env.example .env
# 编辑 .env，把 SK_REPO_PATH 改成本机 SK 仓库路径
docker compose up --build
```

访问：

```text
后端：http://localhost:8000/health
前端：http://localhost:3000
数据库：localhost:5432
```

也可以只启动后端：

```powershell
cd sk-agent
docker compose up --build backend
```

本机 Python 方式仍保留，方便不用 Docker 时调试：

```powershell
cd sk-agent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LOCAL_REPO_PATH="D:\path\to\your\sk-repo"
uvicorn app.main:app --reload --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

读取 canonical：

```powershell
Invoke-RestMethod http://localhost:8000/repo/canonical
```

## 启动前端

Docker Compose 已经包含前端服务。单独启动：

```powershell
cd sk-agent
docker compose up --build frontend
```

本机 Node.js 方式：

```powershell
cd sk-agent\frontend
npm install
npm run dev
```

打开：

```text
http://localhost:3000
```

前端默认读取：

```text
http://localhost:8000
```

如需改后端地址：

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

## 测试

推荐使用 Docker：

```powershell
cd sk-agent
docker compose run --rm backend pytest
```

前端构建检查：

```powershell
cd sk-agent
docker compose run --rm frontend npm run build
```

本机 Python：

```powershell
cd sk-agent\backend
python -m pytest
```

当前测试覆盖：

- `/health` 返回 `{"status": "ok"}`
- 本地读取单个文件
- 缺失文件返回 `not_found`
- 文件树跳过 `.git`
- Markdown 按标题切块

## 索引 API

第 2 期提供：

```text
POST /index/rebuild
GET /index/status
GET /index/chunks?file_path=README.md
```

重建索引：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/index/rebuild
```

查看索引状态：

```powershell
Invoke-RestMethod http://localhost:8000/index/status
```

## 检索与问答 API

第 3 期当前完成了关键词检索和 MiniMax 最小问答：

```text
POST /search
POST /ask
```

关键词检索：

```powershell
$body = @{ query = "MTP 构思招募法在哪"; limit = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post http://localhost:8000/search -ContentType "application/json" -Body $body
```

问答：

```powershell
$body = @{ question = "MTP 构思招募法在哪？"; limit = 6 } | ConvertTo-Json
Invoke-RestMethod -Method Post http://localhost:8000/ask -ContentType "application/json" -Body $body
```

当前 `/ask` 流程：

```text
问题 -> 关键词检索 chunks -> 重新读取命中文件元信息 -> MiniMax 生成答案 -> 返回已读取文件和引用
```

pgvector 语义检索尚未启用。当前没有 MiniMax embedding endpoint、embedding model、Group ID 信息时，系统会稳定运行在关键词检索模式。

已压测的第 3 期问题：

```text
MTP 构思招募法在哪
诊断空白四条件是什么
case-card 格式在哪里
产品评估决策清单有哪些必须条件
```

## 状态审计 API

第 4 期提供规则版状态校准 Agent：

```text
POST /agents/status-audit
```

运行：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/agents/status-audit
```

当前审计固定读取：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

输出包含：

```text
结论
已读取文件
发现的冲突
风险等级
最小修复方案
建议修改文件
Cursor/Codex 执行指令
```

## 入库稿 API

第 5 期提供只生成草稿、不写仓库的入库稿接口：

```text
POST /patch/draft
```

示例：

```powershell
$body = @{
  target_file = "cases/2026/example.md"
  intent = "新增轻量初拆文档"
  new_content = "# Example`n`n正文内容"
  operation = "auto"
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://localhost:8000/patch/draft -ContentType "application/json" -Body $body
```

接口会先读取目标文件，返回已读取文件、建议保存路径、Markdown 正文、diff 预览、commit message、PR title、PR body 和风险提示。`operation=auto` 时，目标文件本次读取成功则生成追加草稿，未读取到则生成新增文件草稿。

## SK 专用 Agent API

第 6 期提供三个工作流接口：

```text
POST /agents/product-teardown
POST /agents/framework-red-team
POST /agents/article-publish-check
```

产品轻量初拆：

```powershell
$body = @{
  product_name = "Example Product"
  notes = "可选补充信息"
  limit = 8
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://localhost:8000/agents/product-teardown -ContentType "application/json" -Body $body
```

框架红队：

```powershell
$body = @{
  idea = "一个 AI 产品方向"
  notes = "可选补充信息"
  limit = 8
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://localhost:8000/agents/framework-red-team -ContentType "application/json" -Body $body
```

文章发布检查：

```powershell
$body = @{
  final_article = "# 标题`n`n文章终稿正文"
  notes = "可选补充信息"
  limit = 8
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://localhost:8000/agents/article-publish-check -ContentType "application/json" -Body $body
```

这些接口都会返回 `read_files`。MiniMax 可用时返回模型生成结果；MiniMax 不可用时返回规则版骨架，并在 `llm.status` 标记为 `unavailable`。

## 前端工作台

第 7 期把主要后端能力接入到首页工作台：

```text
http://localhost:3000
```

当前页面包含：

- 状态：查看 backend、canonical 文件读取、运行状态审计
- 文件：读取文件树并预览文件正文
- 检索：运行 `/search` 和 `/ask`
- 审计：查看状态漂移结果
- Agent：运行产品轻量初拆、框架红队、文章发布检查
- 入库稿：调用 `/patch/draft` 查看草稿和 diff preview

## 图数据库 API

第 8 期接入 Neo4j，并从 PostgreSQL 索引 chunks 重建基础图谱：

```text
POST /graph/rebuild
GET /graph/status
GET /graph/failure-modes/{code}/cases
GET /graph/frameworks/articles?framework=诊断空白
GET /graph/products/tools
GET /graph/theories/reused?min_cases=2
```

启动 Neo4j 与后端：

```powershell
docker compose up -d --build backend
```

重建图谱：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/graph/rebuild
Invoke-RestMethod http://localhost:8000/graph/status
```

Neo4j Browser：

```text
http://localhost:7474
```

## 当前不做

- 不做自动 GitHub 写入
- 不做复杂 LLM Agent
- 不做 pgvector 语义检索

这些都留到后续阶段，先保证仓库读取可靠。
