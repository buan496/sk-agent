# n8n 自动同步 SK 仓库

这个 workflow 用来自动执行：

```text
从 GitHub 下载最新 SK 仓库缓存
↓
重建 PostgreSQL 索引
↓
重建 Neo4j 图谱
↓
读取图谱状态
```

## 1. 配置 Token

不要把 GitHub token 发到聊天里。

把它放进 `sk-agent/.env`：

```env
GITHUB_TOKEN=你的 token
REPO_SYNC_URL=https://github.com/MRYGP/SK.git
REPO_SYNC_PATH=/repo-cache/SK
LOCAL_REPO_PATH=/repo-cache/SK
```

如果 SK 仓库是公开仓库，`GITHUB_TOKEN` 可以为空。  
如果 SK 仓库变成私有仓库，token 需要能读取这个仓库内容。

## 2. 启动服务

```powershell
cd D:\sk-anget-mvp\sk-agent
docker compose up -d --build backend n8n
```

n8n 地址：

```text
http://localhost:5678
```

默认登录信息来自 `.env`：

```env
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=sk_agent_n8n
```

## 3. 导入 Workflow

在 n8n 页面里：

```text
Workflows
Import from File
选择 n8n/workflows/sk-repo-sync.json
```

导入后你会看到：

```text
Manual Trigger
Every 6 Hours
Sync SK Repo
Rebuild Index
Rebuild Graph
Graph Status
```

## 4. 手动运行

打开 workflow，点：

```text
Execute workflow
```

成功后最后一个节点 `Graph Status` 会返回：

```text
status=ok
node_count=...
relationship_count=...
```

## 5. 自动运行

workflow 里已经有 `Every 6 Hours` 节点。

确认没有问题后，把 workflow 右上角切到：

```text
Active
```

它就会每 6 小时自动同步一次。

## 6. 后端同步接口

n8n 调用的是：

```text
POST /repo/sync
POST /index/rebuild
POST /graph/rebuild
GET /graph/status
```

也可以手动测试：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/repo/sync
Invoke-RestMethod -Method Post http://localhost:8000/index/rebuild
Invoke-RestMethod -Method Post http://localhost:8000/graph/rebuild
Invoke-RestMethod http://localhost:8000/graph/status
```

## 7. 安全说明

- `GITHUB_TOKEN` 只放 `.env`。
- `.env` 已经被 `.gitignore` 忽略。
- `/repo/sync` 通过 GitHub zipball API 下载最新仓库缓存，不需要容器安装 git。
- workflow JSON 不包含 token。
