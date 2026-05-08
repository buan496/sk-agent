# Phase 9.4：连接 SKGPT 角色指令仓库

## 本阶段目标

把 `MRYGP/SKGPT` 作为 sk-agent 内部角色的指令来源。SKGPT 只提供角色 prompt / Project Instructions / GPTS 配置，不参与 SK 内容状态判断。

最高优先级仍然是 SK canonical files：

- `README.md`
- `ops/执行状态总表.md`
- `cases/2026/case-index.md`
- `cases/2026/case-cards.md`

## 新增配置

`.env.example` 已增加：

```text
SK_REPO_URL=https://github.com/MRYGP/SK.git
SKGPT_REPO_URL=https://github.com/MRYGP/SKGPT.git
SK_REPO_LOCAL_PATH=
SKGPT_REPO_LOCAL_PATH=
SKGPT_BRANCH=main
```

Docker 后端也会读取 `SKGPT_REPO_URL`、`SKGPT_REPO_LOCAL_PATH` 和 `SKGPT_BRANCH`。

## 新增文件

- `backend/app/services/skgpt_reader.py`
- `backend/app/roles/role_prompt_loader.py`
- `backend/app/api/skgpt.py`
- `memory/role_prompt_mapping.yml`
- `backend/tests/test_skgpt_reader.py`

## 新增 API

```text
GET /skgpt/files
GET /skgpt/file?path=
GET /skgpt/role-prompts
```

这些接口只读取 SKGPT 指令仓库，不读取 SK 内容仓库。

## 角色指令映射

映射文件位于：

```text
memory/role_prompt_mapping.yml
```

格式示例：

```yaml
deep_researcher_role:
  source_repo: SKGPT
  prompt_path: "instructions/deep-researcher.md"
  fallback_prompt_path: null
```

说明：

- `source_repo` 当前只允许 `SKGPT`
- `prompt_path` 不在代码里硬编码，后续只需要修改 YAML
- `deep_research_role` 会兼容映射到当前内部角色 `deep_researcher_role`

## 边界

SKGPT 是角色配置源，不是 SK 当前状态源。

- 不进入 SK 内容索引
- 不覆盖 canonical files
- 不参与状态审计结论
- 不自动写入 SK 仓库
- 不自动 commit / push / PR

## 当前已识别的 SKGPT 指令文件

`/skgpt/files` 当前可读取到：

- `instructions/chatgpt-project-instructions.md`
- `instructions/deep-researcher-gpts-builder-instructions.md`
- `instructions/sk-gpts-system-instructions.md`
- `instructions/sk-product-teardown-gpts-builder-instructions.md`
- `instructions/sk-product-teardown-gpts-instructions.md`

`writing_workshop_role`、`first_reader_role`、`patch_writer_role` 暂未发现一一对应的专用指令文件，所以映射表先使用 fallback prompt。

## 尚未完成

- 后续如果 SKGPT 增加写作工坊、第一读者、入库稿生成器的专用指令，需要更新 `memory/role_prompt_mapping.yml`
- 如果 SKGPT 是私有仓库，需要在 `.env` 配置可读 GitHub token
- 本阶段只连接 prompt 来源，不改变内部角色执行逻辑
