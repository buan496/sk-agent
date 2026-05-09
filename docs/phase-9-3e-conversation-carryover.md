# Phase 9.3e：Conversation Context Carryover

## 为什么“基于以上”不能当新搜索

用户说“基于以上候选来源”“继续”“总结刚才结果”时，真实意图是整理上一轮材料，不是把这句话当成新的搜索 query。

如果直接搜索这句话，结果会偏离研究对象，导致证据账本污染。

## 如何识别承接型指令

新增 `backend/app/services/conversation_intent.py`。

命中以下表达时，视为 `carryover_intent=true`：

- 基于以上
- 根据上面
- 继续
- 接着
- 用刚才的
- 整理以上候选来源
- 基于这些来源
- 不要重新搜索
- 先不联网
- 总结刚才结果

## 如何继承上一轮候选来源

`/roles/run` 增加可选字段：

```json
{
  "conversation_id": "上一轮 run_id",
  "task_type": "deep_research",
  "input": "基于以上候选来源，整理 MYHAIR AI",
  "allow_web": false
}
```

当前轻量实现使用上一轮 `internal_role_runs.id` 作为 `conversation_id`。

系统会继承上一轮：

- `structured_output`
- `evidence_ledger`
- `candidate_sources`
- `missing_evidence`
- `web_queries`

## 什么情况下不允许重新联网

当 `carryover_intent=true` 时：

- 不自动生成新 query
- 不自动调用 web_search
- 优先整理上一轮候选来源

如果没有 `conversation_id` 或找不到上一轮结果，系统返回 warning：

```text
当前请求引用了上一轮结果，但系统没有找到可继承上下文。请在同一对话中继续，或粘贴上一轮候选来源。
```

此时也不重新联网，避免把承接型指令误当搜索词。

## 输出字段

新增：

- `context_used`
- `carryover_intent`
- `inherited_sources_count`
- `new_web_search_performed`

## deep_research_role 承接输出

承接上一轮后会按来源分类整理：

- 官网 / 产品页
- App Store / Google Play
- LinkedIn / Crunchbase
- 媒体报道
- 社区评论
- 未分类来源

并输出：

- 产品功能
- 已有候选证据
- 仍缺证据
- 下一步研究问题
- 不可靠来源剔除建议
