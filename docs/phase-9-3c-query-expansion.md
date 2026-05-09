# Phase 9.3c：Search Query Expansion

## 为什么直接搜索词会失真

用户输入经常很短，例如 `hippocratic`。如果直接拿这个词搜索，搜索引擎可能返回词典、历史、泛化解释，不能稳定命中目标公司或产品。

Query Expansion 的目标是把用户输入扩成更接近研究任务的搜索词，让结果更像研究员会查的内容。

## Query Expansion 如何工作

入口仍然是 `/roles/run`。

规则：

- 如果用户显式填写 `web_queries`，系统优先使用用户输入，不自动扩展。
- 如果 `web_queries` 为空，系统根据 `role_id` 和 `task_type` 自动扩展。
- 每次最多 5 个实际搜索词。
- 返回字段新增 `expanded_queries`，前端显示为“实际搜索词”。

## deep_researcher_role

适用于补外部事实证据、竞品、用户反馈、官方信息。

示例：

输入：

```text
hippocratic
```

扩展为：

```text
Hippocratic AI
Hippocratic AI startup
Hippocratic AI healthcare
Hippocratic AI founder
Hippocratic AI funding
```

## product_teardown_role

适用于产品基本面、融资、定价、竞品和最新状态。

默认扩展方向：

```text
pricing
revenue
funding
competitors
reviews reddit
```

## article_publish_check_role

适用于发布前核查文章中的关键事实和产品现状。

默认扩展方向：

```text
latest
official
announcement
```

## 边界

- Query Expansion 只影响联网搜索词。
- 不修改 canonical preflight。
- 不改变角色业务逻辑。
- 不自动入库。
- 不自动写 SK 仓库。
- 搜索结果仍然只是候选证据。
