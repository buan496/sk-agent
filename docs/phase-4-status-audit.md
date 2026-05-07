# 第 4 期：状态校准 Agent

状态：规则版完成。

## 已完成

- 实现 `backend/app/services/status_auditor.py`
- 固定读取 canonical 文件
- 提取 README 发布状态
- 提取执行状态总表文章状态
- 提取 case-index 文章状态
- 提取 case-cards 案例卡字段
- 检查 README 与执行状态总表是否冲突
- 检查 case-index 与 case-cards 是否冲突
- 检查已发布文章是否仍标待发布
- 检查案例卡是否缺 `depth_draft`
- 检查案例卡是否缺 `article_published`
- 输出最小修复建议
- API：`POST /agents/status-audit`

## 验收

- 容器内后端测试通过：19 passed
- 真实 SK 仓库 canonical 读取成功：4/4
- `/agents/status-audit` 返回 `status=ok`
- 本次审计结果：`risk=high conflict_count=8`

## 运行

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/agents/status-audit
```

## 输出

```text
结论
已读取文件
发现的冲突
风险等级
最小修复方案
建议修改文件
Cursor/Codex 执行指令
```
