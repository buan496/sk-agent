# Phase 9.4：Source Reader 来源正文读取

## 为什么搜索列表不等于研究

搜索结果只有 `title / url / snippet`。Snippet 只是搜索引擎摘要，可能截断、过期或偏离正文。真正研究需要打开来源正文，提取可复核的信息。

Source Reader 的作用是读取候选来源正文，生成候选事实和摘录，但不把它们直接当最终事实。

## source_reader 如何工作

新增：

```text
backend/app/services/source_reader.py
```

输入：

```json
{
  "url": "...",
  "source_type": "official",
  "max_chars": 12000
}
```

输出：

```json
{
  "url": "...",
  "title": "...",
  "clean_text": "...",
  "metadata": {},
  "extracted_facts": [],
  "candidate_claims": [],
  "source_quotes": []
}
```

## 支持的 source_type

第一阶段支持：

- `official`
- `app_store`
- `company_profile`
- `media`

暂不支持：

- PDF
- 视频
- 音频
- XML feed

## API

```http
POST /web/read-source
```

请求：

```json
{
  "url": "https://myhair.ai",
  "source_type": "official"
}
```

## deep_research_role 自动读取

`/roles/run` 新增：

```json
{
  "allow_web": true,
  "read_sources": true
}
```

当 `allow_web=true` 且 `read_sources=true` 时，`deep_research_role` 会在搜索后自动读取：

- top official
- top app_store
- top company_profile

并输出：

- `source_reading_used`
- `read_sources_count`
- `extracted_facts`
- `candidate_claims`
- `source_quotes`

## extracted_facts 与最终事实的区别

`extracted_facts` 只是“从网页正文提取出的候选事实”。它还不是 SK 当前状态，也不是最终事实。

入库前仍需：

- 打开原文复核
- 判断来源是否可靠
- 和 canonical files 对齐
- 人工确认是否生成入库稿

## 边界

- 不自动入库
- 不自动生成最终事实
- 不自动写案例卡
- 不自动 commit
- 不自动 PR
- 不覆盖 canonical files
