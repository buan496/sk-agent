# SK Agent 工作台保姆级说明书

这份文档假设你不是后端工程师、不是前端工程师、也不想先看一堆术语。

目标只有一个：

> 你能知道这个 Agent 是什么、怎么启动、怎么用、哪里坏了怎么看、每个技术栈在里面负责什么，以及接下来怎么一步步学到能自己改。

---

## 0. 先记住一句话

SK Agent 不是一个普通聊天机器人。

它的核心原则是：

> 先读 SK 仓库当前文件，再回答、审计、生成草稿、做图谱查询。

也就是说，它每次工作都应该尽量告诉你：

- 我读了哪些文件
- 读到没有
- 从哪里读的
- 基于什么内容判断
- 不确定就说不确定

---

## 1. 这个项目到底由哪些东西组成？

项目目录大概是这样：

```text
sk-agent/
├─ backend/              后端，负责读仓库、建索引、问答、审计、Agent、图谱
├─ frontend/             前端，浏览器里看到的工作台页面
├─ docs/                 文档
├─ data/repo_cache/      默认的本地仓库挂载占位目录
├─ docker-compose.yml    一键启动所有服务
├─ .env                  你的本地私有配置，不能提交
└─ .env.example          配置模板，可以提交
```

你可以把它理解成一个小公司：

```text
frontend  = 前台接待，给你按钮和页面
backend   = 业务大脑，负责读文件、检索、审计、调用模型
Postgres  = 文档索引仓库，存文件和 chunk
Neo4j     = 关系图谱仓库，存案例、理论、产品之间的关系
MiniMax   = 大模型，负责生成自然语言答案
Docker    = 打包和启动所有服务的工具
GitHub    = 远程代码仓库
n8n       = 自动化流水线，定时同步 SK 仓库并重建索引/图谱
```

---

## 2. 最常用启动命令

进入项目：

```powershell
cd D:\sk-anget-mvp\sk-agent
```

启动所有服务：

```powershell
docker compose up -d --build
```

查看服务状态：

```powershell
docker compose ps
```

停止服务：

```powershell
docker compose down
```

只重启后端：

```powershell
docker compose up -d --build backend
```

只重启前端：

```powershell
docker compose up -d --build frontend
```

---

## 3. 浏览器打开哪些地址？

前端工作台：

```text
http://localhost:3000
```

后端健康检查：

```text
http://localhost:8000/health
```

后端 API 文档：

```text
http://localhost:8000/docs
```

Neo4j 图数据库浏览器：

```text
http://localhost:7474
```

默认 Neo4j 连接信息：

```text
用户名：neo4j
密码：看 .env 里的 NEO4J_PASSWORD
```

---

## 4. .env 是什么？

`.env` 是你的本地私有配置文件。

里面可能有：

- MiniMax API key
- GitHub token
- SK 仓库地址
- 数据库密码
- Neo4j 密码

这个文件不能提交到 GitHub。

当前 `.gitignore` 已经忽略它。

检查 `.env` 是否被忽略：

```powershell
git check-ignore -v .env
```

如果有输出，说明安全。

---

## 5. Docker 是什么？

Docker 的作用是：

> 不让你在电脑上手动装一堆 Python、Node、Postgres、Neo4j，而是用容器统一启动。

本项目里的 Docker 服务：

```text
db        PostgreSQL + pgvector
neo4j     图数据库
backend   FastAPI 后端
frontend  Next.js 前端
```

看容器日志：

```powershell
docker compose logs backend
docker compose logs frontend
docker compose logs db
docker compose logs neo4j
```

持续看日志：

```powershell
docker compose logs -f backend
```

---

## 6. 后端 FastAPI 是什么？

FastAPI 是 Python 后端框架。

它负责提供 API。

比如：

```text
GET  /health
GET  /repo/canonical
POST /index/rebuild
POST /search
POST /ask
POST /agents/status-audit
POST /patch/draft
POST /graph/rebuild
```

核心文件：

```text
backend/app/main.py
```

这个文件负责把各个 API 路由挂上去。

API 文件在：

```text
backend/app/api/
```

服务逻辑在：

```text
backend/app/services/
```

你以后想加一个新后端功能，通常是：

```text
1. 在 services/ 里写业务逻辑
2. 在 api/ 里写接口
3. 在 main.py 里 include_router
4. 在 tests/ 里写测试
```

---

## 7. 前端 Next.js 是什么？

Next.js 是 React 前端框架。

你在浏览器看到的工作台就是它做的。

核心文件：

```text
frontend/app/page.tsx
```

全局样式：

```text
frontend/app/globals.css
```

前端现在有这些页签：

```text
状态
文件
检索
审计
Agent
入库稿
图谱
```

前端的工作方式很简单：

```text
点击按钮
↓
调用后端 API
↓
展示 JSON 或结果文本
```

比如点击“状态审计”，前端会请求：

```text
POST http://localhost:8000/agents/status-audit
```

---

## 8. TypeScript 是什么？

TypeScript 是带类型的 JavaScript。

你会在前端看到这样的东西：

```ts
type SearchResponse = {
  status: string;
  count: number;
  results: SearchHit[];
};
```

它的作用是告诉前端：

> 后端返回的数据大概长什么样。

好处是：

- 写错字段会更容易发现
- 页面不容易乱
- 修改接口时更容易定位问题

---

## 9. Tailwind 是什么？

Tailwind 是 CSS 工具。

你会看到这样的 class：

```tsx
className="rounded-md border border-line bg-white px-4 py-3"
```

它的意思大概是：

```text
rounded-md       中等圆角
border           有边框
border-line      使用 line 颜色
bg-white         白色背景
px-4 py-3        横向/纵向内边距
```

项目里的自定义颜色在：

```text
frontend/tailwind.config.ts
```

常用组件样式在：

```text
frontend/app/globals.css
```

---

## 10. PostgreSQL 是什么？

PostgreSQL 是关系数据库。

本项目用它存：

```text
files       文件元信息
chunks      Markdown 切块
index_runs  每次索引重建记录
```

重建索引：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/index/rebuild
```

查看索引状态：

```powershell
Invoke-RestMethod http://localhost:8000/index/status
```

为什么要索引？

因为不能每次问问题都把整个 SK 仓库塞给模型。

正确流程是：

```text
仓库 Markdown 文件
↓
切成 chunks
↓
存进 PostgreSQL
↓
搜索时先找相关 chunks
↓
再给模型回答
```

---

## 11. pgvector 是什么？

pgvector 是 PostgreSQL 的向量扩展。

它未来用于语义检索。

当前项目状态：

```text
Docker 已使用 pgvector 镜像
但语义 embedding 还没正式接入
当前主要是关键词检索
```

也就是说现在 `/search` 能用，但主要靠关键词。

未来如果接入 MiniMax embedding 或其他 embedding 服务，就可以做：

```text
关键词检索 + 向量检索 + 文件优先级
```

---

## 12. Neo4j 是什么？

Neo4j 是图数据库。

PostgreSQL 擅长存表：

```text
files
chunks
index_runs
```

Neo4j 擅长存关系：

```text
案例 -> 命中 -> 失败模式
文章 -> 引用 -> 案例
产品 -> 有决策 -> 工具
理论 -> 出现于 -> 文件
```

图谱重建：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/graph/rebuild
```

图谱状态：

```powershell
Invoke-RestMethod http://localhost:8000/graph/status
```

几个查询：

```powershell
Invoke-RestMethod http://localhost:8000/graph/failure-modes/FM015/cases
Invoke-RestMethod "http://localhost:8000/graph/frameworks/articles?framework=诊断空白"
Invoke-RestMethod http://localhost:8000/graph/products/tools
Invoke-RestMethod http://localhost:8000/graph/theories/reused
```

重要提醒：

> 图谱来自 PostgreSQL 的 chunks，所以 SK 仓库内容变了，要先 `/index/rebuild`，再 `/graph/rebuild`。

---

## 13. MiniMax 在哪里？

MiniMax 是大模型。

项目用它做：

- `/ask` 问答
- 产品轻量初拆
- 框架红队
- 文章发布检查

配置在 `.env`：

```text
LLM_PROVIDER=minimax
MINIMAX_API_KEY=你的 key
MINIMAX_BASE_URL=你的 MiniMax 地址
MINIMAX_CHAT_ENDPOINT=/chat/completions
MINIMAX_CHAT_MODEL=MiniMax-M2.7
```

检查配置：

```powershell
Invoke-RestMethod http://localhost:8000/llm/config
```

注意：

> API key 永远不要发到聊天里，也不要提交到 GitHub。

---

## 14. GitHub 在这里负责什么？

GitHub 负责保存这个项目代码。

当前代码仓库：

```text
https://github.com/buan496/sk-agent.git
```

查看当前状态：

```powershell
git status --short --branch
```

提交代码：

```powershell
git add .
git commit -m "你的提交说明"
```

推送代码：

```powershell
git push origin main
```

查看远端：

```powershell
git remote -v
```

---

## 15. SK 仓库读取是怎么工作的？

后端有一个服务：

```text
backend/app/services/repo_reader.py
```

它支持两种读法：

```text
LOCAL_REPO_PATH   本地路径
GitHub API/raw    GitHub 仓库
```

读取 canonical 文件：

```powershell
Invoke-RestMethod http://localhost:8000/repo/canonical
```

固定 canonical 文件：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

重要规则：

> 文件没读到，只能说“本次未读取到”，不能断言“文件不存在”。

---

## 15.1 n8n 自动同步是什么？

n8n 是自动化工具。

这次项目里给它做了一条流水线：

```text
从 GitHub 下载最新 SK 仓库
↓
重建 PostgreSQL 索引
↓
重建 Neo4j 图谱
↓
读取图谱状态
```

n8n 地址：

```text
http://localhost:5678
```

workflow 文件：

```text
n8n/workflows/sk-repo-sync.json
```

详细说明：

```text
docs/n8n-sk-sync.md
```

GitHub token 放在 `.env`：

```env
GITHUB_TOKEN=你的 token
```

不要把 token 发到聊天里，也不要提交到 GitHub。

---

## 16. 前端每个页签怎么用？

### 状态

用来看：

- backend 是否在线
- canonical 文件是否读到
- 状态审计入口

先点：

```text
刷新 canonical
```

再点：

```text
运行状态审计
```

### 文件

用来看 SK 仓库文件。

先点：

```text
读取文件树
```

然后点某个文件。

右边会显示文件正文。

### 检索

用来搜索知识库。

你可以试：

```text
MTP 构思招募法在哪
诊断空白四条件是什么
failure_modes
产品评估决策清单
```

### 审计

用来看状态漂移。

它会检查：

- README 和执行状态总表是否冲突
- case-index 和 case-cards 是否冲突
- 已发布文章是否仍标待发布
- 深度底稿是否缺案例卡
- 案例卡是否缺 article_published

### Agent

有三个工作流：

```text
产品轻量初拆
框架红队
文章发布检查
```

产品轻量初拆输入：

```text
产品名
```

框架红队输入：

```text
一个产品想法 / 项目方向
```

文章发布检查输入：

```text
文章终稿
```

### 入库稿

它不会直接改 SK 仓库。

它只生成：

- 建议路径
- Markdown 正文
- diff preview
- commit message
- PR title
- PR body

### 图谱

用来查询关系。

先点：

```text
图谱状态
```

如果图谱旧了，点：

```text
重建图谱
```

可以查询：

```text
哪些案例命中 FM015？
诊断空白框架出现在哪些文章？
哪些产品被判为“工具”？
哪些理论被多个案例引用？
```

---

## 17. 最重要的开发命令

后端测试：

```powershell
docker compose run --rm --no-deps backend pytest
```

前端构建：

```powershell
docker compose run --rm frontend npm run build
```

重建后端：

```powershell
docker compose build backend
```

重建前端：

```powershell
docker compose build frontend
```

查看 API：

```text
http://localhost:8000/docs
```

---

## 18. 常见故障

### 1. 前端打不开

检查：

```powershell
docker compose ps
docker compose logs frontend
```

如果 frontend 没启动：

```powershell
docker compose up -d --build frontend
```

### 2. 后端打不开

检查：

```powershell
docker compose logs backend
```

重启：

```powershell
docker compose up -d --build backend
```

### 3. 数据库没起来

检查：

```powershell
docker compose logs db
```

### 4. Neo4j 没起来

检查：

```powershell
docker compose logs neo4j
```

Neo4j 首次启动可能比后端慢，等一会儿再试。

### 5. MiniMax 报错

检查：

```powershell
Invoke-RestMethod http://localhost:8000/llm/config
```

看：

```text
api_key_configured 是否为 true
base_url 是否正确
model 是否正确
```

### 6. PowerShell 中文乱码

有时 PowerShell 显示中文会乱码，但浏览器里正常。

可以尝试：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## 19. 你怎么一步步学会这个项目？

不要一口气学完。

按这个顺序：

### 第 1 天：只学 Docker

目标：

- 会启动
- 会停止
- 会看日志

练习：

```powershell
docker compose up -d
docker compose ps
docker compose logs backend
docker compose down
```

### 第 2 天：只学 API

目标：

- 会打开 `/docs`
- 会点接口
- 会看返回 JSON

练习：

```text
http://localhost:8000/docs
```

手动试：

```text
/health
/repo/canonical
/index/status
/graph/status
```

### 第 3 天：只学前端

目标：

- 知道页面在 `frontend/app/page.tsx`
- 能改一个按钮文字
- 能重新 build

练习：

```powershell
docker compose run --rm frontend npm run build
docker compose up -d --build frontend
```

### 第 4 天：只学后端

目标：

- 知道 API 在 `backend/app/api`
- 知道业务在 `backend/app/services`
- 能看懂一个简单接口

练习：

打开：

```text
backend/app/api/repo.py
backend/app/services/repo_reader.py
```

### 第 5 天：学数据库索引

目标：

- 知道 Markdown 怎么变成 chunks
- 知道 `/index/rebuild` 干什么

看：

```text
backend/app/services/markdown_parser.py
backend/app/services/indexer.py
```

练习：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/index/rebuild
Invoke-RestMethod http://localhost:8000/index/status
```

### 第 6 天：学 Agent 工作流

目标：

- 知道产品初拆、红队、发布检查怎么组织上下文

看：

```text
backend/app/services/sk_workflow_agents.py
```

练习：

在前端 Agent 页跑三种 Agent。

### 第 7 天：学图数据库

目标：

- 知道节点是什么
- 知道关系是什么
- 会重建图谱

看：

```text
backend/app/services/graph_builder.py
```

练习：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/graph/rebuild
Invoke-RestMethod http://localhost:8000/graph/status
```

---

## 20. 你真正要掌握的 10 个文件

先别看全项目。

先掌握这 10 个：

```text
docker-compose.yml
.env.example
backend/app/main.py
backend/app/config.py
backend/app/services/repo_reader.py
backend/app/services/indexer.py
backend/app/services/retriever.py
backend/app/services/status_auditor.py
backend/app/services/sk_workflow_agents.py
frontend/app/page.tsx
```

学会这 10 个，你就能理解 80%。

---

## 21. 你可以做的 10 个练习

### 练习 1：确认服务都活着

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

### 练习 2：读取 canonical

```powershell
Invoke-RestMethod http://localhost:8000/repo/canonical
```

### 练习 3：重建索引

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/index/rebuild
```

### 练习 4：搜索 MTP

在前端检索页输入：

```text
MTP 构思招募法在哪
```

### 练习 5：跑状态审计

前端点击：

```text
审计 -> 运行状态审计
```

### 练习 6：跑产品初拆

前端点击：

```text
Agent -> 初拆
```

输入：

```text
Perplexity
```

### 练习 7：生成入库稿

前端点击：

```text
入库稿
```

目标文件：

```text
cases/2026/test.md
```

### 练习 8：重建图谱

前端点击：

```text
图谱 -> 重建图谱
```

### 练习 9：改一个前端文案

改：

```text
frontend/app/page.tsx
```

然后：

```powershell
docker compose run --rm frontend npm run build
docker compose up -d --build frontend
```

### 练习 10：加一个新 API

最小流程：

```text
backend/app/api/demo.py
backend/app/main.py include_router
backend/tests/test_demo.py
```

---

## 22. 这个 Agent 现在已经完成到哪里？

当前已经完成：

```text
第 0 期：项目骨架
第 1 期：仓库现读
第 2 期：Markdown 解析与索引
第 3 期：基础检索问答
第 4 期：状态校准 Agent
第 5 期：入库稿生成器
第 6 期：SK 专用 Agent
第 7 期：前端工作台
第 8 期：Neo4j 图数据库
```

当前还可以继续增强：

```text
1. pgvector 语义检索
2. 更精确的图谱抽取
3. 前端结果高亮和引用跳转
4. Agent 输出自动进入入库稿
5. 更完整的测试覆盖
6. 部署到服务器
```

---

## 23. 一句话总图

最后记住这张图：

```text
SK 仓库
  ↓ repo_reader 现读
Markdown 文件
  ↓ markdown_parser
chunks
  ↓ indexer
PostgreSQL
  ↓ retriever
搜索结果
  ↓ MiniMax
问答 / Agent 输出
  ↓ patch_writer
入库稿

PostgreSQL chunks
  ↓ graph_builder
Neo4j 图谱
  ↓ graph API
案例 / 理论 / 产品 / 失败模式关系查询

所有能力
  ↓ frontend
浏览器工作台
```

这就是整个 SK Agent 工作台。
