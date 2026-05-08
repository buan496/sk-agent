# Internal Role System

## 1. 为什么从外部 Agent 记录改成内部角色系统

SK 过去依赖 ChatGPT Project、GPTS、Claude、Codex、Hermes / Cursor 等外部角色。外部角色仍然有用，但它们的输出不是 SK 当前状态。

Phase 9.2 的修正是：把稳定角色内化为 sk-agent 可路由、可审计、可复用的内部角色。外部工具降级为外援，内部角色系统成为本地工作台主线。

## 2. 内部角色列表

- `deep_researcher_role`：深度研究员
- `writing_workshop_role`：写作工坊
- `first_reader_role`：第一读者
- `product_teardown_role`：产品初拆
- `repo_governance_role`：仓库治理副驾
- `article_publish_check_role`：文章发布检查
- `patch_writer_role`：入库稿生成器

## 3. 每个角色的职责和边界

### deep_researcher_role

- 职责：外部事实证据补齐。
- 边界：不宣布入库，不替代状态审计，必须输出 A/B/C/X 证据等级。

### writing_workshop_role

- 职责：公众号文章改写和传播表达。
- 边界：不做最终事实核查，不擅自改变核心判断，保留“那一刀”。

### first_reader_role

- 职责：陌生读者视角审稿。
- 边界：不事实核查，不直接改正文。

### product_teardown_role

- 职责：产品轻量初拆和排重。
- 边界：必须读 canonical files，不直接宣布入库。

### repo_governance_role

- 职责：状态漂移、任务路由、双仓边界和维护建议。
- 边界：不直接写仓库，不越过人工确认。

### article_publish_check_role

- ????????????????????????
- ???????????????????????????

### patch_writer_role

- 职责：生成可审核入库稿。
- 边界：不 commit，不 push，不自动 PR。

## 4. 角色路由规则

- `deep_research` -> `deep_researcher_role`
- `writing_workshop` -> `writing_workshop_role`
- `first_reader` -> `first_reader_role`
- `product_teardown` -> `product_teardown_role`
- `repo_governance` -> `repo_governance_role`
- `patch_draft` -> `patch_writer_role`
- `status_audit` -> `repo_governance_role`
- `article_publish_check` -> `article_publish_check_role`

## 5. 角色输出 schema

`POST /roles/run` 统一返回：

```text
role_id
role_name
conclusion
read_files
risks
minimal_next_step
answer_markdown
structured_output
```

各角色的专属字段放在 `structured_output` 中。

## 6. canonical files 为什么仍然最高优先级

canonical files 是 SK 当前状态 SSOT：

```text
README.md
ops/执行状态总表.md
cases/2026/case-index.md
cases/2026/case-cards.md
```

内部角色、memory、graph、vector、历史运行记录都不能覆盖 canonical files。

## 7. 外部 GPTS / Claude / Codex 如何作为外援

外部 GPTS / Claude / Codex / Hermes 仍然可用，但它们只是外援：

- 输出不是 SK 当前状态。
- 必须人工复核。
- 需要入库时走 patch draft。
- 入库后才影响 SK 状态。

Phase 9.4 之后，SKGPT 仓库可以作为内部角色的 prompt 来源。它只提供角色指令，不提供 SK 当前状态。角色指令映射由 `memory/role_prompt_mapping.yml` 管理，读取入口是 `/skgpt/role-prompts`。

## 8. 如何运行 /roles/run

```http
POST /roles/run
```

```json
{
  "task_type": "first_reader",
  "input": "文章草稿",
  "notes": "请从陌生读者视角检查",
  "preferred_role": null
}
```

## 9. 如何查看 internal_role_runs

```http
GET /roles/runs?limit=10
```

该记录只用于审计和复盘，不作为 SK 当前状态来源。
