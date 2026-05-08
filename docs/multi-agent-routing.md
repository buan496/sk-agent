# Multi-Agent Routing

## 1. 多智能体角色分工

## ChatGPT Project

- 状态判断
- 流程设计
- 任务路由
- 仓库治理建议

适合回答“下一步该交给谁”“这个任务是否该入库”“是否偏离 SK 原则”。

## GPTS 深度研究员

- 外部资料补齐
- 产品基本面
- 创始人原话
- 竞品
- 用户反馈
- 市场证据

输出必须带证据等级 A/B/C/X。没有证据等级的输出只能作为候选材料。

## Claude

- 长文推演
- 写作改稿
- 复杂长上下文整理

Claude 可以做长文和推演，但做状态判断前必须读取当前仓库。

## Codex

- sk-agent 工程实现
- 测试
- API
- 前端
- 文档

Codex 不得自动修改 SK 内容仓库，不得绕过人工确认。

## Hermes / Cursor

- 仓库自动化执行
- 批量文件修改
- PR 草稿

必须人工复核后再执行，不得静默修改 canonical files。

## sk-agent

- 本地工作台
- 状态审计
- 检索
- Agent schema
- 入库稿生成

sk-agent 不能绕过人工主权，不能把候选材料当成当前状态。

## 2. 路由规则

- 需要外部事实证据 -> GPTS 深度研究员
- 需要长文改写 / 推演 -> Claude
- 需要工程实现 -> Codex
- 需要批量改文件 -> Hermes / Cursor
- 需要当前状态校准 -> sk-agent
- 需要任务路由判断 -> ChatGPT Project
- 需要可审核入库材料 -> sk-agent `/patch/draft`

## 3. 入库规则

- 外部 AI 输出不直接进入 SK 当前状态。
- 外部 AI 输出必须经过人工复核。
- 需要入库时生成 patch draft。
- 入库后才更新相关状态文件。
- canonical files 始终高于 memory、graph、vector、external_agent_runs。

## 4. 记录规则

外部 GPTS / Claude / Codex / Hermes / Cursor 的重要结果，应通过：

```text
POST /memory/external-run
```

记录为候选材料。记录本身不代表入库，不代表当前 SK 状态。
