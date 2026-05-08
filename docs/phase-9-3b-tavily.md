# Phase 9.3b：接入真实 Tavily 搜索

## 目标

把 `/web/search` 从默认 mock 搜索升级为真实 Tavily 搜索。Tavily 只用于内部角色补候选证据，不替代 SK 仓库当前文件。

## 配置

在 `.env` 中填写：

```text
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=你的 Tavily Key
```

如果没有 `TAVILY_API_KEY`，系统会使用 mock provider。

如果 Tavily 请求失败，系统会自动 fallback 到 mock provider，并在返回的 `warnings` 中说明。

## API

```http
POST /web/search
```

请求：

```json
{
  "query": "Luffu pricing founder quote",
  "limit": 5
}
```

返回：

```json
{
  "query": "...",
  "provider": "tavily",
  "results": [
    {
      "title": "...",
      "url": "...",
      "snippet": "...",
      "source_type": "official",
      "fetched_at": "2026-05-08T17:00:00+08:00",
      "provider": "tavily"
    }
  ],
  "warnings": []
}
```

## source_type 分类

系统仍然保留四类：

- `official`
- `media`
- `community`
- `unknown`

分类由 URL 规则粗分，只用于候选证据排序，不是最终事实判断。

## 证据等级

联网结果仍然只生成 candidate：

- `official` -> `A_candidate`
- `media` -> `B_candidate`
- `community` -> `C_candidate`
- `unknown` -> `X_candidate`

最终 A/B/C/X 需要人工或后续审查确认。

## 边界

- 不修改角色系统
- 不修改 canonical preflight
- 不自动写 SK 仓库
- 不自动入库
- 不自动 commit / push / PR
- Tavily 结果不能覆盖 canonical files
