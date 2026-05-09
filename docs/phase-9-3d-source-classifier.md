# Phase 9.3d：Source Type Classifier 优化

## 目标

真实 Tavily 搜索已经可用，但原来的 `official/media/community/unknown` 分类太粗，很多有效来源会被误判成 `unknown`。本阶段新增独立来源分类器，让证据账本更容易阅读。

## 来源分类规则

### official

适用：

- URL domain 与搜索对象高度匹配
- 例如 `myhair.ai`、`openai.com`、`anthropic.com`
- 官方文档、开发者文档、支持中心、`.gov`、`.edu`

默认证据等级：

```text
A_candidate
```

### app_store

适用：

- `play.google.com`
- `apps.apple.com`

默认证据等级：

```text
B_candidate
```

如果用于评分、评论、更新时间、下载量等应用商店元数据：

```text
A_candidate_for_app_metadata
```

### company_profile

适用：

- `linkedin.com/company`
- `crunchbase.com`
- `pitchbook.com`
- `wellfound.com`

默认证据等级：

```text
B_candidate
```

LinkedIn / Crunchbase 不能直接当官方事实完全引用，需要复核。

### media

适用：

- `techcrunch.com`
- `wired.com`
- `theverge.com`
- `businesswire.com`
- `prnewswire.com`
- `forbes.com`
- `36kr.com`
- `techbuzz.ai`

默认证据等级：

```text
B_candidate
```

如果是 PR Newswire / BusinessWire 公司新闻稿：

```text
A_candidate_for_announcement
```

### community

适用：

- `reddit.com`
- `news.ycombinator.com`
- `x.com`
- `twitter.com`
- `quora.com`
- `zhihu.com`

默认证据等级：

```text
C_candidate
```

### unknown

无法分类时：

```text
X_candidate
```

## source_reason

每条搜索结果新增：

```text
source_reason
```

示例：

- `domain matches product official site`
- `Google Play app listing`
- `company profile database`
- `media report`
- `company announcement wire`
- `community discussion`
- `unclassified source`

## candidate 不等于最终证据等级

`A_candidate` 只代表“来源类型上更接近高可信来源”，不代表已经完成事实核查。

最终证据等级仍需人工或后续审查确认。

## 为什么官方域名仍需人工复核

官方域名也可能出现：

- 页面过期
- 只宣传不披露关键事实
- 产品线不同
- 地区版本不同
- 搜索结果命中错误页面

所以 official 只是更高优先级候选来源，不能自动写入 SK 仓库。
