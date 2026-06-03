# Phase 10 Research State Engine

## 1. 本阶段目标

Phase 10 的目标是建立 Research Reading Loop：

```text
搜索 -> 找来源 -> 读取来源正文 -> 抽取候选事实 -> 形成研究状态 -> 驱动下一步判断
```

本阶段不新增 Agent，不做 UI 大改，不写 SK 仓库。

## 2. 新增能力

新增 Research State Engine，用来保存一个研究对象的长期候选状态：

- 研究对象：例如 MYHAIR AI、Hippocratic AI、Luffu
- 候选来源：官网、应用商店、LinkedIn、Crunchbase、媒体文章等
- 来源读取状态：candidate / read / read_failed
- 候选事实：从来源正文中抽出的 facts 和 claims
- 证据缺口：还缺哪些来源、哪些事实仍未确认
- 下一步动作：应该读哪个来源、复核哪些候选事实

## 3. 新增数据库表

### research_objects

保存研究对象。

关键字段：

- slug
- name
- status
- research_target
- summary
- notes

### research_sources

保存研究对象关联的候选来源。

关键字段：

- object_id
- url
- title
- source_type
- source_reason
- evidence_level
- read_status
- clean_text
- metadata_json
- extracted_facts_json
- candidate_claims_json
- source_quotes_json
- last_read_at

### research_facts

保存从来源中抽取出的候选事实。

关键字段：

- object_id
- source_id
- fact_text
- source_url
- source_type
- evidence_level
- confidence
- status
- notes

## 4. 新增后端服务

新增：

```text
backend/app/services/research_state.py
```

主要职责：

- 创建或读取 research object
- 添加候选来源
- 调用 source_reader 读取正文
- 把 extracted_facts / candidate_claims 写入 research_facts
- 从 internal_role_runs 导入 evidence_ledger 和 source_readings
- 汇总当前研究状态、缺口、风险和下一步动作

## 5. 新增 API

```text
POST /research/objects
GET  /research/objects?limit=50
GET  /research/objects/{slug}/state
POST /research/objects/{slug}/sources
POST /research/objects/{slug}/read-source
POST /research/objects/{slug}/ingest-role-run
```

## 6. 使用示例

### 创建研究对象

```json
POST /research/objects
{
  "name": "MYHAIR AI",
  "slug": "myhair-ai"
}
```

### 添加候选来源

```json
POST /research/objects/myhair-ai/sources
{
  "url": "https://www.myhair.ai/",
  "title": "MYHAIR AI",
  "source_type": "official",
  "source_reason": "domain matches product official site"
}
```

### 读取来源正文并抽候选事实

```json
POST /research/objects/myhair-ai/read-source
{
  "url": "https://www.myhair.ai/",
  "source_type": "official"
}
```

### 导入一次内部角色运行结果

```json
POST /research/objects/myhair-ai/ingest-role-run
{
  "run_id": 123
}
```

## 7. 研究状态如何判断

Research State 会返回：

- object
- sources
- facts
- counts
- gaps
- risks
- next_actions

其中 gaps 目前是轻量规则：

- 缺官网 / 产品页来源
- 缺应用商店 / 用户反馈来源
- 缺公司资料来源
- 候选来源还没有读取正文
- 还没有人工确认过的事实

## 8. 最高优先级不变

Research State 不是 SK 当前状态。

它只是候选研究状态，用来帮助下一步判断。当前状态仍然以 SK canonical files 为准：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

Research State 不能覆盖：

- canonical files
- 状态审计结果
- 人工复核判断
- 入库后的 SK 仓库状态

## 9. 安全边界

本阶段不会：

- 自动写 SK 仓库
- 自动 commit
- 自动 push
- 自动创建 PR
- 自动入库
- 把候选事实当作最终事实
- 用联网结果覆盖 canonical files

## 10. 已完成

- 新增 research_objects / research_sources / research_facts
- 新增 research_state 服务
- 新增 /research API
- 支持来源读取结果沉淀为候选事实
- 支持导入 internal_role_runs 的 evidence_ledger / source_readings
- 新增后端测试

## 11. 未完成

- 前端 Research State 页面暂未做
- 候选事实的人工确认 / 驳回接口暂未做
- Research Object 与 case-card / article 状态的显式关联暂未做
- 多来源事实合并与冲突检测暂未做
