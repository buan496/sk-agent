# Phase 9.3：内部角色可控联网

## 为什么一开始不联网

sk-agent 的第一原则是先读取 SK 仓库当前文件，再输出判断。联网信息变化快、来源质量不稳定，所以不能替代 SK canonical files。

canonical files 仍然最高优先级：

- `README.md`
- `ops/执行状态总表.md`
- `cases/2026/case-index.md`
- `cases/2026/case-cards.md`

## 哪些角色允许联网

当前只允许：

- `deep_researcher_role`
- `product_teardown_role`
- `article_publish_check_role`

其他角色即使传入 `allow_web=true`，也只返回 warning，不执行联网。

## allow_web 怎么用

`POST /roles/run` 增加：

```json
{
  "task_type": "deep_research",
  "input": "研究 Luffu 是否值得进入 SK",
  "notes": "",
  "preferred_role": null,
  "allow_web": true,
  "web_queries": ["Luffu pricing founder quote"]
}
```

- `allow_web=false`：不联网，只输出证据缺口。
- `allow_web=true`：允许可联网角色调用 web search。
- 每次最多 5 个 query。
- 每个 query 最多 5 条结果。
- 搜索失败不影响 canonical preflight 和角色基本输出。

## web_queries 怎么用

前端里“可选：每行一个搜索词；留空则由角色自动生成”。

留空时，系统会用任务输入作为搜索词。

## 证据等级 candidate 规则

联网结果只标候选等级：

- `official` -> `A_candidate`
- `media` -> `B_candidate`
- `community` -> `C_candidate`
- `unknown` -> `X_candidate`

注意：候选等级不是最终 A/B/C/X。最终证据等级需要人工或后续审查确认。

## 联网结果为什么不能覆盖 canonical files

联网结果可能过期、误读、二手转述或来源不清。它只能补“外部证据候选”，不能改变 SK 当前状态。

禁止：

- 自动写 SK 仓库
- 自动入库
- 自动 commit / push / PR
- 把社区信息当 A 级证据
- 让联网结果替代 canonical files

## 如何配置 WEB_SEARCH_PROVIDER

`.env`：

```text
WEB_SEARCH_PROVIDER=mock
TAVILY_API_KEY=
```

## 如何使用 mock provider

默认就是 mock，不需要 API key。适合本地开发和测试。

```http
POST /web/search
```

```json
{
  "query": "Luffu pricing founder quote",
  "limit": 5
}
```

## 如何配置 Tavily

`.env`：

```text
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=你的 Tavily Key
```

如果没有 key，即使 provider 写成 tavily，系统也会回退到 mock。

## 如何在前端使用

进入“Memory / 内部角色”区域：

1. 选择角色任务，例如“深度研究”或“产品初拆”。
2. 勾选“允许联网补证据”。
3. 可选填写搜索词，每行一个。
4. 点击“运行角色”。
5. 查看“是否联网 / 搜索词 / 证据账本 / 缺失证据 / warnings”。
