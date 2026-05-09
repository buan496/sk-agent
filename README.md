# SK Agent 工作台

本项目是一个本地优先的 **SK 仓库 Agent 工作台**。

它的第一原则不是聊天，而是：

> 先读取 SK 仓库当前文件，明确读了什么，再输出判断、风险和入库稿。

当前工作台已经具备：

- 读取 SK 仓库 canonical files
- 仓库文件浏览
- Markdown 索引与检索
- 状态漂移审计
- 入库稿草案生成
- 图谱查询
- 内部角色系统
- Tavily 联网搜索
- Query Expansion
- 来源分类
- 来源正文读取
- 多轮承接上下文

## 1. 快速启动

在项目根目录运行：

```powershell
cd d:\sk-anget-mvp\sk-agent
docker compose up -d backend frontend
```

访问：

```text
前端：http://localhost:3000
后端：http://localhost:8000/health
```

局域网访问时，把 `localhost` 换成本机 IP，例如：

```text
http://192.168.1.9:3000
```

## 2. 环境变量

真实密钥只放 `.env`，不要提交。

`.env.example` 只是模板。

常用配置：

```env
SK_REPO_URL=https://github.com/MRYGP/SK.git
SKGPT_REPO_URL=https://github.com/MRYGP/SKGPT.git
LOCAL_REPO_PATH=/repo-cache/SK
REPO_SYNC_URL=https://github.com/MRYGP/SK.git
REPO_SYNC_PATH=/repo-cache/SK

LLM_PROVIDER=minimax
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_CHAT_ENDPOINT=/chat/completions
MINIMAX_CHAT_MODEL=MiniMax-M2.7

WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
```

如果换了 `.env`，重启后端：

```powershell
docker compose up -d --force-recreate backend
```

## 3. SK / SKGPT 双仓边界

### SK 仓库

`MRYGP/SK`

用途：

- 内容
- 案例
- 状态
- 方法论
- 执行状态

SK 是当前状态来源。

### SKGPT 仓库

`MRYGP/SKGPT`

用途：

- Project Instructions
- GPTS 配置
- 上传清单
- 现读协议
- 内部角色 prompt 来源

SKGPT 不是 SK 当前状态来源。

## 4. Canonical Files

回答型接口必须优先读取这 4 个文件：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

如果本次没读到，只能说：

```text
本次未读取到
```

不能推断文件不存在。

## 5. 前端怎么用

打开：

```text
http://localhost:3000
```

页面入口：

- **状态**：查看后端健康、canonical 文件读取状态、手动拉取 SK 仓库
- **文件**：浏览和阅读 SK 仓库文件
- **检索**：搜索知识库，并可点击阅读命中文件
- **审计**：运行状态漂移审计
- **Agent**：运行产品初拆、框架红队、文章发布检查
- **入库稿**：生成可审核 patch draft
- **图谱**：查询案例、框架、产品、理论关系
- **Memory / 内部角色**：运行内部角色、联网补证据、读取来源正文

## 6. 内部角色

内部角色入口在前端 **Memory / 内部角色**。

当前角色：

- 深度研究员
- 写作工坊
- 第一读者
- 产品初拆
- 仓库治理
- 文章发布检查
- 入库稿生成器

联网只允许：

- `deep_researcher_role`
- `product_teardown_role`
- `article_publish_check_role`

其他角色即使勾选联网，也只会返回 warning。

## 7. 联网搜索

当前使用 Tavily。

后端接口：

```text
POST /web/search
```

示例：

```json
{
  "query": "myhair.ai official",
  "limit": 5
}
```

搜索结果包含：

- title
- url
- snippet
- source_type
- source_reason
- fetched_at
- provider

如果 Tavily 失败，会自动 fallback 到 mock provider。

## 8. Query Expansion

如果用户没有手填搜索词，系统会自动扩展。

例：

输入：

```text
hippocratic
```

深度研究员会实际搜索：

```text
Hippocratic AI
Hippocratic AI startup
Hippocratic AI healthcare
Hippocratic AI founder
Hippocratic AI funding
```

如果用户手动填写 `web_queries`，系统优先使用用户输入，不自动扩展。

## 9. 来源分类

搜索结果会被分类为：

- `official`
- `app_store`
- `company_profile`
- `media`
- `community`
- `unknown`

证据等级只作为候选：

- `official` -> `A_candidate`
- `app_store` -> `B_candidate`
- `company_profile` -> `B_candidate`
- `media` -> `B_candidate`
- `community` -> `C_candidate`
- `unknown` -> `X_candidate`

候选等级不等于最终事实等级。

## 10. 来源正文读取

后端接口：

```text
POST /web/read-source
```

示例：

```json
{
  "url": "https://www.myhair.ai/",
  "source_type": "official"
}
```

返回：

- title
- clean_text
- metadata
- extracted_facts
- candidate_claims
- source_quotes

前端中，在内部角色运行结果的候选来源下，可以点击：

```text
读取正文
```

支持：

- official
- app_store
- company_profile
- media

暂不支持：

- PDF
- 视频
- 音频
- XML feed

## 11. 多轮承接上下文

如果用户在同一个前端页面里先跑一轮联网研究，再输入：

```text
基于以上候选来源，整理 MYHAIR AI 的产品功能、证据缺口、下一步研究问题
```

系统会识别为承接型指令：

- 不重新搜索
- 不重新生成 query
- 继承上一轮 evidence_ledger
- 基于上一轮候选来源整理报告

前端会显示：

- 是否使用上一轮上下文
- 是否重新联网
- 继承来源数量

## 12. 常用后端 API

```text
GET  /health
GET  /repo/files
GET  /repo/file?path=
GET  /repo/canonical
POST /repo/sync

POST /index/rebuild
GET  /index/status
GET  /index/chunks?file_path=

POST /search
POST /ask

POST /agents/status-audit
POST /agents/product-teardown
POST /agents/framework-red-team
POST /agents/article-publish-check

POST /patch/draft

GET  /graph/status
POST /graph/rebuild
GET  /graph/failure-modes/{code}/cases
GET  /graph/frameworks/articles?framework=
GET  /graph/products/tools
GET  /graph/theories/reused

GET  /roles
POST /roles/run
GET  /roles/runs?limit=10

POST /web/search
POST /web/read-source

GET  /skgpt/files
GET  /skgpt/file?path=
GET  /skgpt/role-prompts
```

## 13. 测试

后端：

```powershell
docker compose run --rm backend pytest
```

前端：

```powershell
docker compose run --rm frontend npm run build
```

当前最后一次验证：

```text
后端：75 passed
前端：next build passed
```

## 14. 重要文档

- `docs/beginner-manual.md`：新手说明书
- `docs/architecture.md`：架构说明
- `docs/phase-checklist.md`：阶段完成清单
- `docs/internal-role-system.md`：内部角色系统
- `docs/phase-9-3-controlled-web-search.md`：可控联网
- `docs/phase-9-3c-query-expansion.md`：搜索词扩展
- `docs/phase-9-3d-source-classifier.md`：来源分类
- `docs/phase-9-3e-conversation-carryover.md`：上下文承接
- `docs/phase-9-4-source-reader.md`：来源正文读取
- `docs/phase-8-audit.md`：Phase 8 后验收审计

## 15. 安全边界

当前系统不会：

- 自动写 SK 仓库
- 自动 commit
- 自动 push
- 自动创建 PR
- 自动入库
- 自动修改案例卡
- 让联网结果覆盖 canonical files
- 把外部搜索结果当成最终事实

所有联网搜索、来源正文、图谱、memory、历史运行记录，都只是辅助层。

最终状态仍以 SK canonical files 为准。

## 16. 交接建议

交接时优先检查：

1. `.env` 是否有 `TAVILY_API_KEY`
2. `docker compose ps` 是否 backend / frontend / db / neo4j 正常
3. `http://localhost:3000` 是否能打开
4. `http://localhost:8000/health` 是否返回 ok
5. 前端“状态”页 canonical files 是否读取正常
6. 前端“Memory / 内部角色”能否运行深度研究
7. 勾选联网后是否返回 Tavily 来源
8. 点击“读取正文”是否能读取 official 来源正文
