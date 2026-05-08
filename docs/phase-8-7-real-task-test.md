# Phase 8.7 真实任务压测报告

测试时间：2026-05-08

测试原则：

- 只调用现有 API。
- 不新增功能。
- 不修改架构。
- 不写入 SK 仓库。
- 不执行自动 commit / push / PR。

## 1. 总结论

5 个真实任务接口均成功返回。

总体判断：通过 Phase 8.7 压测，但发现 3 类需要后续关注的问题：

- SK 仓库当前存在真实状态漂移：状态审计发现 8 个审计项，其中 high=3。
- 部分工作流固定候选路径与 SK 当前文件名不完全一致，但 fallback 检索能读到替代文件。
- `/patch/draft` 是入库稿草稿接口，不是 Agent 接口，因此没有 Agent schema 字段；报告中已做归一化展示。

## 2. 压测任务 1：状态漂移审计

接口：`POST /agents/status-audit`

输入：

```text
无参数，运行状态漂移审计。
```

read_files：

```text
README.md                                            ok / local
ops/执行状态总表.md                                  ok / local
cases/2026/case-index.md                             ok / local
cases/2026/case-cards.md                             ok / local
```

conclusion：

```text
发现 8 个状态审计项：high=3, medium=0, low=5。
```

risks：

```text
README 与执行状态总表对文章 001 的状态口径不一致。
README 与执行状态总表对文章 006 的状态口径不一致。
README 与执行状态总表对文章 011 的状态口径不一致。
CASE-REF-Lovable 缺少 depth_draft 字段，无法回链深度底稿。
CASE-007-Paid 缺少 depth_draft 字段，无法回链深度底稿。
CASE-REF-WHF 缺少 depth_draft 字段，无法回链深度底稿。
CASE-REF-PandaCake 缺少 depth_draft 字段，无法回链深度底稿。
CASE-013 缺少 depth_draft 字段，无法回链深度底稿。
```

minimal_next_step：

```text
确认文章 001 的真实状态，并只改动 README 或执行状态总表中落后的那一处。
```

ingest_draft：

```text
required: true
reason: 状态审计只生成最小修复建议，不直接写仓库。
suggested_files:
- README.md
- ops/执行状态总表.md
- cases/2026/case-cards.md
```

是否通过验收：通过。

发现的问题：

- canonical 读取顺序正确。
- schema 字段完整。
- 发现真实状态漂移，后续应先做最小修复草稿，不建议继续扩大功能。

## 3. 压测任务 2：产品轻量初拆

接口：`POST /agents/product-teardown`

输入：

```text
product_name=Perplexity Comet
notes=浏览器形态的 AI 搜索/助理产品，用于压测仓库排重、模板读取和入库建议。
```

read_files：

```text
README.md                                            ok / local
ops/执行状态总表.md                                  ok / local
cases/2026/case-index.md                             ok / local
cases/2026/case-cards.md                             ok / local
core/product-teardown-template.md                    ok / local
content/article_template.md                          ok / local
cases/2026/深度底稿/ListenLabs-轻量初拆.md            ok / local
cases/2026/深度底稿/Supermemory-轻量初拆.md           ok / local
radar/product-radar.md                               ok / local
meta/CLAUDE系统指令.md                                ok / local
cases/2026/产品对标库-38个AI产品复制价值排名.md        ok / local
cases/2026/RRF案例验证库.md                           ok / local
```

conclusion：

```text
入库判断：check_duplicate；状态审计风险：high。
```

risks：

```text
状态审计发现 8 个冲突，入库前需要先校准。
仓库已有相关命中，入库前需要排重。
```

minimal_next_step：

```text
先读取检索命中文件做排重，确认不是重复内容后再生成 /patch/draft 入库稿。
```

ingest_draft：

```text
decision: check_duplicate
reason: 本次检索到 6 个相关片段，入库前需要先排重和确认是否补充已有文件。
suggested_path: cases/2026/perplexity-comet-teardown.md
```

是否通过验收：通过。

发现的问题：

- canonical 读取顺序正确。
- schema 字段完整。
- 工作流没有直接建议写库，而是要求先排重，符合“先生成可审核入库稿”的原则。
- 当前状态漂移为 high，会影响任何入库判断的可靠性。

## 4. 压测任务 3：框架红队

接口：`POST /agents/framework-red-team`

输入：

```text
idea=给独立创作者做 AI 知识库审计工作台
notes=本地优先，读取 GitHub/本地仓库，输出状态漂移、风险和入库稿。
```

read_files：

```text
README.md                                            ok / local
ops/执行状态总表.md                                  ok / local
cases/2026/case-index.md                             ok / local
cases/2026/case-cards.md                             ok / local
core/项目审问清单.md                                  ok / local
core/产品评估决策清单.md                              not_found / 本次未读取到
core/failure_modes.yml                               ok / local
core/SKILL-真实产品外部体检与机会推演SOP.md           ok / local
meta/CLAUDE系统指令.md                                ok / local
core/产品评估决策清单-v1.0.md                         ok / local
cases/2026/深度底稿/Tesla-素材底稿.md                 ok / local
content/公众号内容生产经验手册.md                      ok / local
cases/2026/产品对标库-38个AI产品复制价值排名.md        ok / local
```

conclusion：

```text
反向排雷结果
```

risks：

```text
部分工作流参考文件本次未读取到：core/产品评估决策清单.md
```

minimal_next_step：

```text
补充目标用户、场景、替代方案和可验证证据；必要时再生成入库稿。
```

ingest_draft：

```text
required: false
reason: 框架红队输出先用于判断，入库前需要人工确认。
```

是否通过验收：通过，但有路径问题。

发现的问题：

- canonical 读取顺序正确。
- schema 字段完整。
- 固定候选路径 `core/产品评估决策清单.md` 本次未读取到。
- fallback 检索读到了 `core/产品评估决策清单-v1.0.md`，说明内容可用，但候选路径应在后续按 SK 当前文件名校准。

## 5. 压测任务 4：文章发布检查

接口：`POST /agents/article-publish-check`

输入：

```text
一篇关于 AI 知识库审计工作台的短文章终稿。
```

read_files：

```text
README.md                                            ok / local
ops/执行状态总表.md                                  ok / local
cases/2026/case-index.md                             ok / local
cases/2026/case-cards.md                             ok / local
content/公众号写作指南.md                             ok / local
content/内容生产经验手册.md                           not_found / 本次未读取到
content/文章发布SOP.md                               ok / local
content/article_template.md                          ok / local
meta/gpts-deep-researcher-GPTs-Instructions-v1.3.1.md ok / local
meta/CLAUDE系统指令.md                                ok / local
content/公众号内容生产经验手册.md                      ok / local
cases/2026/research-wechat-visibility.md             ok / local
cases/2026/_archive/散思考/备稿-充电宝文章-待定发布时机.md ok / local
```

conclusion：

```text
文章发布检查报告
```

risks：

```text
部分工作流参考文件本次未读取到：content/内容生产经验手册.md
```

minimal_next_step：

```text
按风险检查修订终稿，确认事实、案例状态和发布清单后再发布。
```

ingest_draft：

```text
required: false
reason: 发布检查结果不自动入库；如需入库，应走 /patch/draft 生成草稿。
```

是否通过验收：通过，但有路径问题。

发现的问题：

- canonical 读取顺序正确。
- schema 字段完整。
- 固定候选路径 `content/内容生产经验手册.md` 本次未读取到。
- fallback 检索读到了 `content/公众号内容生产经验手册.md`，说明应后续校准候选路径。
- 搜索结果读到了 `meta/gpts-deep-researcher-GPTs-Instructions-v1.3.1.md`，这是 SKGPT/GPTS 类材料，说明检索层仍可能把 meta 指令文件混入回答上下文；这与 Phase 8.5 的双仓边界目标存在轻微偏移风险。

## 6. 压测任务 5：入库稿生成

接口：`POST /patch/draft`

输入：

```text
target_file=cases/2026/perplexity-comet-teardown.md
intent=新增 Perplexity Comet 轻量初拆草稿，用于人工审核后决定是否入库。
operation=auto
```

read_files：

```text
cases/2026/perplexity-comet-teardown.md              not_found / 本次未读取到
```

conclusion：

```text
目标文件本次未读取到；草稿建议按新增文件生成 cases/2026/perplexity-comet-teardown.md。
```

risks：

```text
目标文件本次未读取到，不等于文件不存在；入库前需要再次确认路径。
```

minimal_next_step：

```text
人工审核 diff_preview、Markdown 正文、commit message、PR title 和 PR body 后，再决定是否入库。
```

ingest_draft：

```text
suggested_save_path: cases/2026/perplexity-comet-teardown.md
markdown_body: 已生成
diff_preview: 已生成
commit_message: 已生成
pr_title: 已生成
pr_body: 已生成
```

是否通过验收：通过。

发现的问题：

- `/patch/draft` 没有写入 SK 仓库，符合限制。
- 目标文件本次未读取到时，接口没有推断文件不存在，符合原则。
- `/patch/draft` 不是 Agent 接口，所以原生响应不包含 `conclusion/evidence/risks/minimal_next_step/ingest_draft/answer_markdown` 这组 Agent schema。本报告已按压测要求归一化展示。

## 7. 总体验收判断

```text
状态漂移审计：通过
产品轻量初拆：通过
框架红队：通过，但需校准候选路径
文章发布检查：通过，但需校准候选路径，并注意 meta/GPTS 指令文件混入检索上下文
入库稿生成：通过
```

## 8. 后续建议

1. 先处理状态审计发现的 high 风险状态漂移。
2. 校准工作流候选路径：
   - `core/产品评估决策清单.md` -> 当前实际可读文件可能是 `core/产品评估决策清单-v1.0.md`
   - `content/内容生产经验手册.md` -> 当前实际可读文件可能是 `content/公众号内容生产经验手册.md`
3. 检索层后续应进一步排除 SKGPT/GPTS/meta 指令类文件，避免混入 SK 内容判断。
4. `/patch/draft` 可以保持草稿接口定位，不建议为了 schema 统一而把它改成 Agent。
