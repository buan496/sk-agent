# Cognitive Flow OS

## 1. 为什么从 Workflow System 转向 Cognitive Flow

Phase 10 已经建立了 Research State Engine，可以保存研究对象、候选来源、正文读取和候选事实。

但实际使用中，用户不是按后台流程工作：

- 先创建对象
- 再添加来源
- 再读取来源
- 再导入角色结果

用户真实工作方式更像：

- 边想边判断
- 连续追问
- 临时联想
- 动态切换方向
- 不断修正判断
- 最后才沉淀

所以 Phase 11 把默认入口从 workflow-first 改成 cognitive-flow-first。

## 2. 用户真实工作方式

用户默认只需要输入一句话，例如：

```text
MYHAIR AI 会不会最后变成卖药渠道？
```

系统自动完成：

- 识别当前实体：MYHAIR AI
- 建立或继承 cognitive session
- 自动关联 research object
- 读取 canonical files
- 维护当前判断
- 维护风险和未解决问题
- 必要时调用内部 role 作为 cognitive operator
- 把判断演化写入 judgment evolution

用户不用手动说：

- 创建 research object
- ingest role run
- 基于以上
- 继续上一轮

## 3. 为什么 Research Management 不适合当前 SK

Research Management 更适合明确项目流：

```text
对象 -> 来源 -> 正文 -> 事实 -> 报告
```

但 SK 的核心不是管理材料，而是判断形成：

```text
思考 -> 怀疑 -> 证据 -> 风险 -> 修正判断 -> 入库候选
```

因此 Research State 仍保留，但从主入口降级为后台状态层。

## 4. Cognitive Session

Cognitive Session 不是普通 chat session。

它保存的是当前认知状态：

- current_topic
- active_entity_slug
- current_judgment
- evidence
- risks
- unresolved_questions
- next_question
- operator_used
- research_object_slug

新增表：

```text
cognitive_sessions
cognitive_entities
cognitive_messages
cognitive_judgments
```

## 5. Thought Continuity

同一个 cognitive session 内，系统默认继承上一轮：

- 当前研究对象
- 当前判断
- 当前 evidence ledger
- 当前风险
- 当前未解决问题

用户不需要说“继续”或“基于以上”。

如果用户输入：

```text
那它的信任冲突在哪里？
```

系统会默认把“它”挂回当前主题，而不是当成一个全新任务。

## 6. Judgment Evolution

系统记录的不是聊天流水账，而是判断如何演化。

例如：

```text
t1: AI hair analysis
t2: diagnosis gap structure
t3: possible commerce funnel
t4: trust conflict risk
t5: consumer healthcare category
```

对应 API：

```text
GET /cognitive/sessions/{session_id}/state
```

返回 judgment_evolution。

## 7. Internal Roles 降级为 Operators

Phase 11 后，用户默认不需要显式选择 role。

Internal Roles 仍保留，但成为系统内部 cognitive operators：

- deep_research_role：补外部候选证据
- first_reader_role：读者视角
- repo_governance_role：状态治理
- patch_writer_role：入库稿草案

当前第一版只在用户允许联网时自动调用 deep_research_role。

## 8. 前端为什么从后台改成思维工作台

旧前端更像后台管理：

- 文件页
- 搜索页
- Agent 页
- 入库稿页
- Memory 页

Phase 11 的前端主入口改为：

- 左侧：当前实体 / 当前主题 / 最近思维流
- 中间：连续思考流
- 右侧：当前判断 / 当前证据 / 当前风险 / 未解决问题 / 下一问
- 底部：自由输入框

默认不再要求“先选 role 再执行”。

## 9. 新增 API

```text
POST /cognitive/think
GET  /cognitive/sessions?limit=20
GET  /cognitive/sessions/{session_id}/state
```

## 10. 安全边界

Phase 11 不会：

- 自动写 SK 仓库
- 自动 commit
- 自动 push
- 自动创建 PR
- 自动入库
- 做复杂 autonomous agent
- 做无限上下文 replay

仍然坚持：

- canonical files 最高优先级
- 人工主权
- evidence candidate 机制
- 可审计性

## 11. 当前未完成

- 自动 operator 路由仍然是轻量规则
- 暂未实现事实确认 / 驳回界面
- 暂未把所有旧工作台入口迁移到新前端
- 暂未实现多实体之间的正式图谱写入
- 暂未实现长期 recurring patterns 自动沉淀
