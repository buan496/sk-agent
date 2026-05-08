"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthResponse = { status?: string };

type RepoFileMeta = {
  path: string;
  size: number;
  last_modified: string | null;
  source: string;
};

type FileReadResult = {
  status: string;
  path?: string;
  message?: string;
  content?: string | null;
  source?: string;
  file?: RepoFileMeta | null;
};

type CanonicalResponse = {
  status: string;
  read_count: number;
  total: number;
  files: FileReadResult[];
};

type FilesResponse = {
  status: string;
  source?: string;
  count: number;
  files: RepoFileMeta[];
  message?: string;
};

type SearchHit = {
  file_path: string;
  heading?: string | null;
  excerpt?: string;
  start_line: number;
  end_line: number;
  total_score: number;
};

type SearchResponse = {
  status: string;
  query: string;
  mode?: string;
  count: number;
  read_files: string[];
  results: SearchHit[];
};

type AskResponse = {
  status: string;
  answer?: string;
  answer_markdown?: string;
  read_files?: ReadFileSummary[];
  citations?: Array<{
    file_path: string;
    start_line: number;
    end_line: number;
    heading?: string | null;
  }>;
  detail?: string;
};

type ReadFileSummary = {
  path?: string;
  status?: string;
  source?: string;
  size?: number;
  last_modified?: string | null;
  message?: string;
};

type StatusAuditResponse = {
  status: string;
  conclusion?: string;
  read_files?: ReadFileSummary[];
  summary?: Record<string, unknown>;
  conflicts?: Array<{
    check: string;
    risk_level: string;
    message: string;
    suggested_files?: string[];
  }>;
  risk_level?: string;
  minimal_fix_plan?: string[];
  codex_instruction?: string;
};

type AgentResponse = {
  status: string;
  agent?: string;
  conclusion?: string;
  read_files?: ReadFileSummary[];
  evidence?: unknown;
  risks?: string[];
  minimal_next_step?: string;
  ingest_draft?: unknown;
  answer_markdown?: string;
  answer?: string;
  llm?: { status?: string; provider?: string; model?: string; message?: string };
  ingest_recommendation?: Record<string, unknown>;
  search?: { count?: number; read_files?: string[] };
  detail?: string;
};

type AgentRunRecord = {
  time: string;
  agent: string;
  input: string;
  read_files: ReadFileSummary[];
  risks: string[];
  conclusion: string;
};

type PatchDraftResponse = {
  status: string;
  target_file?: string;
  operation?: string;
  suggested_save_path?: string;
  read_files?: ReadFileSummary[];
  markdown_body?: string;
  diff_summary?: { summary?: string; intent?: string };
  diff_preview?: string;
  commit_message?: string;
  pr_title?: string;
  pr_body?: string;
  risk_notes?: string[];
  detail?: string;
};

type RepoSyncResponse = {
  status: string;
  action?: string;
  repo?: string;
  branch?: string;
  target_path?: string;
  commit?: string | null;
  message?: string;
  detail?: string;
};

type GraphStatusResponse = {
  status: string;
  node_count?: number;
  relationship_count?: number;
  labels?: Array<{ label: string; count: number }> | Record<string, number>;
  relationship_types?: Array<{ type: string; count: number }> | Record<string, number>;
  latest_index_run?: Record<string, unknown> | null;
  graph_rebuild_time?: string | null;
  source_chunk_count?: number;
  canonical_read_status?: Record<string, unknown>;
  detail?: string;
};

type GraphQueryResponse = {
  status: string;
  query: string;
  count: number;
  results: Array<Record<string, unknown>>;
  detail?: string;
};

type MemoryRegistriesResponse = {
  status: string;
  internal_roles?: string;
  agent_registry: string;
  gpts_registry: string;
  external_tools: string;
  detail?: string;
};

type ExternalRun = {
  id: number;
  created_at: string;
  agent_type: string;
  agent_name: string;
  task_type: string;
  input_summary: string;
  output_summary: string;
  source_link_or_file?: string;
  related_sk_files: string[];
  status: string;
  should_ingest: boolean;
  ingested: boolean;
  notes?: string;
};

type ExternalRunsResponse = {
  status: string;
  count: number;
  runs: ExternalRun[];
  detail?: string;
};

type ExternalRunForm = {
  agent_type: string;
  agent_name: string;
  task_type: string;
  input_summary: string;
  output_summary: string;
  source_link_or_file: string;
  related_sk_files: string;
  status: string;
  should_ingest: boolean;
  ingested: boolean;
  notes: string;
};

type RoleInfo = {
  role_id: string;
  role_name: string;
  purpose: string;
};

type RoleListResponse = {
  status: string;
  roles: RoleInfo[];
};

type RoleRunResponse = {
  status: string;
  role_id: string;
  role_name: string;
  task_type: string;
  conclusion: string;
  read_files: ReadFileSummary[];
  risks: string[];
  minimal_next_step: string;
  answer_markdown: string;
  human_readable_markdown?: string;
  structured_output: Record<string, unknown>;
  web_used?: boolean;
  web_queries?: string[];
  web_results_count?: number;
  evidence_ledger?: unknown[];
  missing_evidence?: unknown[];
  warnings?: string[];
  run_id?: number;
};

type InternalRoleRun = RoleRunResponse & {
  id: number;
  created_at: string;
  input_summary: string;
  should_ingest: boolean;
  ingested: boolean;
};

type InternalRoleRunsResponse = {
  status: string;
  count: number;
  runs: InternalRoleRun[];
};

type RoleRunForm = {
  task_type: string;
  input: string;
  notes: string;
  preferred_role: string;
  allow_web: boolean;
  web_queries: string;
};

type TabKey = "home" | "files" | "search" | "audit" | "agents" | "patch" | "graph" | "memory";
type AgentMode = "product-teardown" | "framework-red-team" | "article-publish-check";
type GraphQueryKind = "fm015" | "framework" | "tools" | "theories";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "home", label: "状态" },
  { key: "files", label: "文件" },
  { key: "search", label: "检索" },
  { key: "audit", label: "审计" },
  { key: "agents", label: "Agent" },
  { key: "patch", label: "入库稿" },
  { key: "graph", label: "图谱" },
  { key: "memory", label: "内部角色" },
];

const canonicalPaths = [
  "README.md",
  "ops/执行状态总表.md",
  "cases/2026/case-index.md",
  "cases/2026/case-cards.md",
];

const quickSearches = ["MTP 构思招募法在哪", "诊断空白四条件是什么", "failure_modes", "产品评估决策清单"];

const roleTaskLabels: Record<string, string> = {
  deep_research: "深度研究：整理外部证据清单",
  writing_workshop: "写作工坊：改文章结构和表达",
  first_reader: "第一读者：从读者视角审稿",
  product_teardown: "产品初拆：轻量初拆和排重",
  repo_governance: "仓库治理：状态和边界判断",
  patch_draft: "入库稿：生成可审核草稿",
  status_audit: "状态审计：检查状态漂移",
  article_publish_check: "发布检查：文章发布前检查",
};

function apiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";
    if (!configured || (!isLocalhost && configured.includes("localhost"))) {
      return `${window.location.protocol}//${hostname}:8000`;
    }
  }
  return configured ?? "http://localhost:8000";
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.detail === "string" ? payload.detail : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

function statusText(status?: string) {
  if (status === "ok") return "已读取";
  if (status === "not_found") return "本次未读取到";
  if (status === "partial") return "部分读取";
  if (status === "error") return "错误";
  if (status === "not_configured") return "未配置";
  if (status === "repo_path_unavailable") return "路径不可读";
  return status || "-";
}

function compact(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

function bulletList(value: unknown, fallback = "-") {
  if (!value) return fallback;
  if (Array.isArray(value)) {
    const lines = value
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          const title = record.source_title || record.title || record.claim || "候选来源";
          const url = record.source_url || record.url;
          const sourceType = record.source_type || "unknown";
          const level = record.evidence_level || "candidate";
          return url ? `${title}（${sourceType}，${level}）\n${url}` : `${title}（${sourceType}，${level}）`;
        }
        return String(item);
      })
      .filter(Boolean);
    return lines.length ? lines.map((line) => `- ${line}`).join("\n") : fallback;
  }
  return compact(value);
}

function formatShanghaiTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [health, setHealth] = useState<"ok" | "offline">("offline");
  const [apiDisplay, setApiDisplay] = useState("loading");
  const [showIntro, setShowIntro] = useState(true);
  const [canonical, setCanonical] = useState<CanonicalResponse | null>(null);
  const [files, setFiles] = useState<FilesResponse | null>(null);
  const [selectedPath, setSelectedPath] = useState("README.md");
  const [fileResult, setFileResult] = useState<FileReadResult | null>(null);
  const [searchQuery, setSearchQuery] = useState("MTP 构思招募法在哪");
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [askQuestion, setAskQuestion] = useState("诊断空白四条件是什么");
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [auditResult, setAuditResult] = useState<StatusAuditResponse | null>(null);
  const [syncResult, setSyncResult] = useState<RepoSyncResponse | null>(null);
  const [agentMode, setAgentMode] = useState<AgentMode>("product-teardown");
  const [agentInput, setAgentInput] = useState("Perplexity");
  const [agentNotes, setAgentNotes] = useState("");
  const [agentResult, setAgentResult] = useState<AgentResponse | null>(null);
  const [agentRuns, setAgentRuns] = useState<AgentRunRecord[]>([]);
  const [patchTarget, setPatchTarget] = useState("cases/2026/example.md");
  const [patchIntent, setPatchIntent] = useState("新增轻量初拆文档");
  const [patchContent, setPatchContent] = useState("# Example\n\n正文内容");
  const [patchResult, setPatchResult] = useState<PatchDraftResponse | null>(null);
  const [graphStatus, setGraphStatus] = useState<GraphStatusResponse | null>(null);
  const [graphQueryKind, setGraphQueryKind] = useState<GraphQueryKind>("fm015");
  const [graphQuery, setGraphQuery] = useState("FM015");
  const [graphResult, setGraphResult] = useState<GraphQueryResponse | null>(null);
  const [memoryRegistries, setMemoryRegistries] = useState<MemoryRegistriesResponse | null>(null);
  const [externalRuns, setExternalRuns] = useState<ExternalRunsResponse | null>(null);
  const [externalRunForm, setExternalRunForm] = useState<ExternalRunForm>({
    agent_type: "gpts",
    agent_name: "深度研究员",
    task_type: "external_research",
    input_summary: "",
    output_summary: "",
    source_link_or_file: "",
    related_sk_files: "",
    status: "draft",
    should_ingest: false,
    ingested: false,
    notes: "",
  });
  const [roleList, setRoleList] = useState<RoleListResponse | null>(null);
  const [roleRuns, setRoleRuns] = useState<InternalRoleRunsResponse | null>(null);
  const [roleResult, setRoleResult] = useState<RoleRunResponse | null>(null);
  const [roleRunForm, setRoleRunForm] = useState<RoleRunForm>({
    task_type: "deep_research",
    input: "研究一个产品是否值得进入 SK。",
    notes: "",
    preferred_role: "",
    allow_web: false,
    web_queries: "",
  });
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState<string>("");

  const canonicalByPath = useMemo(() => {
    return new Map((canonical?.files ?? []).map((item) => [item.path, item]));
  }, [canonical]);

  useEffect(() => {
    setApiDisplay(apiBaseUrl());
    void refreshSnapshot();
  }, []);

  async function run<T>(label: string, task: () => Promise<T>): Promise<T | null> {
    setBusy(label);
    setError("");
    try {
      return await task();
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : String(errorValue));
      return null;
    } finally {
      setBusy("");
    }
  }

  async function refreshSnapshot() {
    await run("刷新状态", async () => {
      const [healthPayload, canonicalPayload] = await Promise.all([
        fetchJson<HealthResponse>("/health"),
        fetchJson<CanonicalResponse>("/repo/canonical"),
      ]);
      setHealth(healthPayload.status === "ok" ? "ok" : "offline");
      setCanonical(canonicalPayload);
      return true;
    });
  }

  async function loadFiles() {
    const result = await run("读取文件树", () => fetchJson<FilesResponse>("/repo/files"));
    if (result) setFiles(result);
  }

  async function readFile(path = selectedPath) {
    const result = await run("读取文件", () => fetchJson<FileReadResult>(`/repo/file?path=${encodeURIComponent(path)}`));
    if (result) {
      setSelectedPath(path);
      setFileResult(result);
    }
  }

  async function runSearch(query = searchQuery) {
    const result = await run("检索", () =>
      fetchJson<SearchResponse>("/search", {
        method: "POST",
        body: JSON.stringify({ query, limit: 8 }),
      }),
    );
    if (result) {
      setSearchQuery(query);
      setSearchResult(result);
    }
  }

  async function runAsk(event?: FormEvent) {
    event?.preventDefault();
    const result = await run("问答", () =>
      fetchJson<AskResponse>("/ask", {
        method: "POST",
        body: JSON.stringify({ question: askQuestion, limit: 6 }),
      }),
    );
    if (result) setAskResult(result);
  }

  async function runAudit() {
    const result = await run("状态审计", () =>
      fetchJson<StatusAuditResponse>("/agents/status-audit", { method: "POST", body: "{}" }),
    );
    if (result) setAuditResult(result);
  }

  async function syncRepo() {
    const result = await run("拉取 SK 仓库", () =>
      fetchJson<RepoSyncResponse>("/repo/sync", {
        method: "POST",
        body: "{}",
      }),
    );
    if (result) {
      setSyncResult(result);
      await refreshSnapshot();
    }
  }

  async function runAgent(event: FormEvent) {
    event.preventDefault();
    const body =
      agentMode === "product-teardown"
        ? { product_name: agentInput, notes: agentNotes, limit: 6 }
        : agentMode === "framework-red-team"
          ? { idea: agentInput, notes: agentNotes, limit: 6 }
          : { final_article: agentInput, notes: agentNotes, limit: 6 };
    const result = await run("运行 Agent", () =>
      fetchJson<AgentResponse>(`/agents/${agentMode}`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    );
    if (result) {
      setAgentResult(result);
      setAgentRuns((previous) => [
        {
          time: new Date().toISOString(),
          agent: result.agent || agentMode,
          input: agentInput,
          read_files: result.read_files ?? [],
          risks: result.risks ?? [],
          conclusion: result.conclusion ?? "",
        },
        ...previous,
      ].slice(0, 10));
    }
  }

  async function runPatch(event: FormEvent) {
    event.preventDefault();
    const result = await run("生成入库稿", () =>
      fetchJson<PatchDraftResponse>("/patch/draft", {
        method: "POST",
        body: JSON.stringify({
          target_file: patchTarget,
          intent: patchIntent,
          new_content: patchContent,
          operation: "auto",
        }),
      }),
    );
    if (result) setPatchResult(result);
  }

  async function refreshGraphStatus() {
    const result = await run("读取图谱状态", () => fetchJson<GraphStatusResponse>("/graph/status"));
    if (result) setGraphStatus(result);
  }

  async function rebuildGraph() {
    const result = await run("重建图谱", () =>
      fetchJson<GraphStatusResponse>("/graph/rebuild", {
        method: "POST",
        body: "{}",
      }),
    );
    if (result) setGraphStatus(result);
  }

  async function runGraphQuery(event?: FormEvent) {
    event?.preventDefault();
    const endpoint =
      graphQueryKind === "fm015"
        ? `/graph/failure-modes/${encodeURIComponent(graphQuery || "FM015")}/cases`
        : graphQueryKind === "framework"
          ? `/graph/frameworks/articles?framework=${encodeURIComponent(graphQuery || "诊断空白")}`
          : graphQueryKind === "tools"
            ? "/graph/products/tools"
            : "/graph/theories/reused";
    const result = await run("查询图谱", () => fetchJson<GraphQueryResponse>(endpoint));
    if (result) setGraphResult(result);
  }

  async function loadMemoryRegistries() {
    const result = await run("读取多智能体分工", () => fetchJson<MemoryRegistriesResponse>("/memory/registries"));
    if (result) setMemoryRegistries(result);
  }

  async function loadExternalRuns() {
    const result = await run("读取外部任务记录", () => fetchJson<ExternalRunsResponse>("/memory/external-runs?limit=20"));
    if (result) setExternalRuns(result);
  }

  async function submitExternalRun(event: FormEvent) {
    event.preventDefault();
    const related_sk_files = externalRunForm.related_sk_files
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    const result = await run("记录外部任务", () =>
      fetchJson<{ status: string; run: ExternalRun }>("/memory/external-run", {
        method: "POST",
        body: JSON.stringify({
          ...externalRunForm,
          related_sk_files,
        }),
      }),
    );
    if (result) {
      await loadExternalRuns();
    }
  }

  async function loadRoleList() {
    const result = await run("读取内部角色", () => fetchJson<RoleListResponse>("/roles"));
    if (result) setRoleList(result);
  }

  async function loadRoleRuns() {
    const result = await run("读取角色运行记录", () => fetchJson<InternalRoleRunsResponse>("/roles/runs?limit=10"));
    if (result) setRoleRuns(result);
  }

  async function runInternalRole(event: FormEvent) {
    event.preventDefault();
    const result = await run("运行内部角色", () =>
      fetchJson<RoleRunResponse>("/roles/run", {
        method: "POST",
        body: JSON.stringify({
          task_type: roleRunForm.task_type,
          input: roleRunForm.input,
          notes: roleRunForm.notes,
          preferred_role: roleRunForm.preferred_role || null,
          allow_web: roleRunForm.allow_web,
          web_queries: roleRunForm.web_queries
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      }),
    );
    if (result) {
      setRoleResult(result);
      await loadRoleRuns();
    }
  }

  return (
    <main className="min-h-screen bg-panel text-ink">
      {showIntro && <IntroModal close={() => setShowIntro(false)} />}
      <header className="border-b border-line bg-white">
        <div className="mx-auto max-w-7xl px-5 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-medium text-accent">Local-first SK repository workbench</p>
              <h1 className="mt-1 text-3xl font-semibold">SK Agent 工作台</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <Metric label="Backend" value={health} tone={health === "ok" ? "good" : "bad"} />
              <Metric label="Canonical" value={canonical ? `${canonical.read_count}/${canonical.total}` : "0/4"} />
              <Metric label="API" value={apiDisplay} />
            </div>
          </div>
          <nav className="mt-5 flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`h-10 rounded-md border px-4 text-sm font-medium ${
                  activeTab === tab.key
                    ? "border-accent bg-accent text-white"
                    : "border-line bg-white text-slate-700 hover:border-accent"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-5">
        {(busy || error) && (
          <div className="mb-4 rounded-md border border-line bg-white px-4 py-3 text-sm">
            {busy && <span className="font-medium text-accent">{busy}中...</span>}
            {error && <span className="font-medium text-red-700">{error}</span>}
          </div>
        )}

        {activeTab === "home" && (
          <HomeView
            canonical={canonical}
            canonicalByPath={canonicalByPath}
            refreshSnapshot={refreshSnapshot}
            syncRepo={syncRepo}
            syncResult={syncResult}
            runAudit={runAudit}
            auditResult={auditResult}
          />
        )}
        {activeTab === "files" && (
          <FilesView
            files={files}
            selectedPath={selectedPath}
            setSelectedPath={setSelectedPath}
            fileResult={fileResult}
            loadFiles={loadFiles}
            readFile={readFile}
          />
        )}
        {activeTab === "search" && (
          <SearchView
            query={searchQuery}
            setQuery={setSearchQuery}
            result={searchResult}
            runSearch={runSearch}
            askQuestion={askQuestion}
            setAskQuestion={setAskQuestion}
            askResult={askResult}
            runAsk={runAsk}
            openFileFromSearch={async (path) => {
              await readFile(path);
              setActiveTab("files");
            }}
          />
        )}
        {activeTab === "audit" && <AuditView result={auditResult} runAudit={runAudit} />}
        {activeTab === "agents" && (
          <AgentsView
            mode={agentMode}
            setMode={setAgentMode}
            input={agentInput}
            setInput={setAgentInput}
            notes={agentNotes}
            setNotes={setAgentNotes}
            result={agentResult}
            history={agentRuns}
            runAgent={runAgent}
          />
        )}
        {activeTab === "patch" && (
          <PatchView
            target={patchTarget}
            setTarget={setPatchTarget}
            intent={patchIntent}
            setIntent={setPatchIntent}
            content={patchContent}
            setContent={setPatchContent}
            result={patchResult}
            runPatch={runPatch}
          />
        )}
        {activeTab === "graph" && (
          <GraphView
            status={graphStatus}
            queryKind={graphQueryKind}
            setQueryKind={setGraphQueryKind}
            query={graphQuery}
            setQuery={setGraphQuery}
            result={graphResult}
            refreshStatus={refreshGraphStatus}
            rebuildGraph={rebuildGraph}
            runQuery={runGraphQuery}
            openFileFromGraph={async (path) => {
              await readFile(path);
              setActiveTab("files");
            }}
          />
        )}
        {activeTab === "memory" && (
          <InternalRolesView
            roles={roleList}
            runs={roleRuns}
            result={roleResult}
            form={roleRunForm}
            setForm={setRoleRunForm}
            loadRoles={loadRoleList}
            loadRuns={loadRoleRuns}
            runRole={runInternalRole}
          />
        )}
      </div>
    </main>
  );
}

function IntroModal({ close }: { close: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4">
      <div className="w-full max-w-lg rounded-md border border-line bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">SK Agent 工作台怎么用</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">先确认仓库状态，再检索和运行 Agent，最后只生成可审核入库稿。</p>
          </div>
          <button className="secondary-button shrink-0" type="button" onClick={close}>
            关闭
          </button>
        </div>
        <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
          <div>
            <span className="font-semibold">1. 首页：</span>
            点“手动拉取 SK 仓库”和“刷新 canonical”，确认核心文件是 4/4。
          </div>
          <div>
            <span className="font-semibold">2. 审计页：</span>
            先运行状态审计；如果有 high 风险，先处理状态漂移。
          </div>
          <div>
            <span className="font-semibold">3. 检索/图谱：</span>
            搜到结果后点“阅读文件”，只相信已读取文件里的证据。
          </div>
          <div>
            <span className="font-semibold">4. Agent/入库稿：</span>
            运行初拆、红队或发布检查；需要入库时只生成草稿，不会自动写 SK 仓库。
          </div>
        </div>
        <button className="primary-button mt-5 w-full" type="button" onClick={close}>
          开始使用
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  const color = tone === "good" ? "text-accent" : tone === "bad" ? "text-red-700" : "text-slate-900";
  return (
    <div className="min-w-28 rounded-md border border-line bg-panel px-3 py-2">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className={`mt-1 truncate text-sm font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function HomeView({
  canonical,
  canonicalByPath,
  refreshSnapshot,
  syncRepo,
  syncResult,
  runAudit,
  auditResult,
}: {
  canonical: CanonicalResponse | null;
  canonicalByPath: Map<string | undefined, FileReadResult>;
  refreshSnapshot: () => Promise<void>;
  syncRepo: () => Promise<void>;
  syncResult: RepoSyncResponse | null;
  runAudit: () => Promise<void>;
  auditResult: StatusAuditResponse | null;
}) {
  return (
    <>
      <Section title="当前仓库状态">
        <div className="flex flex-wrap gap-3">
          <button className="primary-button" type="button" onClick={refreshSnapshot}>
            刷新 canonical
          </button>
          <button className="secondary-button" type="button" onClick={syncRepo}>
            手动拉取 SK 仓库
          </button>
          <button className="secondary-button" type="button" onClick={runAudit}>
            运行状态审计
          </button>
        </div>
      </Section>
      {syncResult && (
        <Section title="最近同步">
          <KeyValue
            rows={[
              ["状态", syncResult.status],
              ["仓库", syncResult.repo],
              ["分支", syncResult.branch],
              ["commit", syncResult.commit],
              ["缓存路径", syncResult.target_path],
              ["说明", syncResult.message],
            ]}
          />
        </Section>
      )}
      <div className="overflow-hidden rounded-md border border-line bg-white">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="border-b border-line bg-panel text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">文件</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">来源</th>
              <th className="px-4 py-3">大小</th>
              <th className="px-4 py-3">更新时间</th>
            </tr>
          </thead>
          <tbody>
            {canonicalPaths.map((path) => {
              const item = canonicalByPath.get(path);
              const meta = item?.file;
              return (
                <tr key={path} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-medium">{path}</td>
                  <td className="px-4 py-3">{statusText(item?.status ?? canonical?.status)}</td>
                  <td className="px-4 py-3 text-slate-600">{meta?.source ?? item?.source ?? "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{meta ? `${meta.size} B` : "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{formatShanghaiTime(meta?.last_modified)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {auditResult && (
        <Section title="最近审计">
          <KeyValue rows={[["风险等级", auditResult.risk_level], ["冲突数", auditResult.summary?.conflict_count]]} />
        </Section>
      )}
    </>
  );
}

function FilesView({
  files,
  selectedPath,
  setSelectedPath,
  fileResult,
  loadFiles,
  readFile,
}: {
  files: FilesResponse | null;
  selectedPath: string;
  setSelectedPath: (value: string) => void;
  fileResult: FileReadResult | null;
  loadFiles: () => Promise<void>;
  readFile: (path?: string) => Promise<void>;
}) {
  const visibleFiles = (files?.files ?? []).slice(0, 120);
  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <section>
        <div className="mb-3 flex gap-2">
          <button className="primary-button" type="button" onClick={loadFiles}>
            读取文件树
          </button>
          <button className="secondary-button" type="button" onClick={() => readFile()}>
            读取文件
          </button>
        </div>
        <input className="field mb-3" value={selectedPath} onChange={(event) => setSelectedPath(event.target.value)} />
        <div className="max-h-[620px] overflow-auto rounded-md border border-line bg-white">
          {visibleFiles.map((file) => (
            <button
              key={file.path}
              type="button"
              className="block w-full border-b border-line px-3 py-2 text-left text-sm hover:bg-panel"
              onClick={() => readFile(file.path)}
            >
              <div className="font-medium">{file.path}</div>
              <div className="text-xs text-slate-500">{file.size} B</div>
            </button>
          ))}
          {!files && <div className="px-3 py-3 text-sm text-slate-600">点击读取文件树。</div>}
        </div>
      </section>
      <section className="min-w-0">
        <ResultHeader title={fileResult?.path || selectedPath} status={fileResult?.status} />
        <pre className="code-block min-h-[620px]">{fileResult?.content || fileResult?.message || "尚未读取文件。"}</pre>
      </section>
    </div>
  );
}

function SearchView({
  query,
  setQuery,
  result,
  runSearch,
  askQuestion,
  setAskQuestion,
  askResult,
  runAsk,
  openFileFromSearch,
}: {
  query: string;
  setQuery: (value: string) => void;
  result: SearchResponse | null;
  runSearch: (query?: string) => Promise<void>;
  askQuestion: string;
  setAskQuestion: (value: string) => void;
  askResult: AskResponse | null;
  runAsk: (event?: FormEvent) => Promise<void>;
  openFileFromSearch: (path: string) => Promise<void>;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
      <section>
        <form
          className="mb-3 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            void runSearch();
          }}
        >
          <input className="field" value={query} onChange={(event) => setQuery(event.target.value)} />
          <button className="primary-button" type="submit">
            检索
          </button>
        </form>
        <div className="mb-4 flex flex-wrap gap-2">
          {quickSearches.map((item) => (
            <button key={item} className="secondary-button" type="button" onClick={() => runSearch(item)}>
              {item}
            </button>
          ))}
        </div>
        <ResultList result={result} openFile={openFileFromSearch} />
      </section>
      <section>
        <form className="mb-3 flex gap-2" onSubmit={runAsk}>
          <input className="field" value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} />
          <button className="primary-button" type="submit">
            问答
          </button>
        </form>
        <ReadFilesList files={askResult?.read_files ?? []} />
        <pre className="code-block mt-3 min-h-80">
          {askResult?.answer_markdown || askResult?.answer || askResult?.detail || "尚未运行问答。"}
        </pre>
      </section>
    </div>
  );
}

function AuditView({ result, runAudit }: { result: StatusAuditResponse | null; runAudit: () => Promise<void> }) {
  return (
    <>
      <button className="primary-button mb-4" type="button" onClick={runAudit}>
        运行状态审计
      </button>
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <section>
          <KeyValue
            rows={[
              ["状态", result?.status],
              ["风险等级", result?.risk_level],
              ["冲突数", result?.summary?.conflict_count],
              ["案例卡数量", result?.summary?.case_card_count],
            ]}
          />
          <ReadFilesList files={result?.read_files ?? []} />
        </section>
        <section>
          <ResultHeader title="冲突" status={result?.risk_level} />
          <div className="space-y-3">
            {(result?.conflicts ?? []).map((conflict, index) => (
              <div key={`${conflict.check}-${index}`} className="rounded-md border border-line bg-white p-4">
                <div className="text-sm font-semibold">{conflict.check}</div>
                <div className="mt-1 text-sm text-red-700">{conflict.risk_level}</div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{conflict.message}</p>
              </div>
            ))}
            {!result && <div className="rounded-md border border-line bg-white p-4 text-sm">尚未运行审计。</div>}
          </div>
        </section>
      </div>
    </>
  );
}

function AgentsView({
  mode,
  setMode,
  input,
  setInput,
  notes,
  setNotes,
  result,
  history,
  runAgent,
}: {
  mode: AgentMode;
  setMode: (value: AgentMode) => void;
  input: string;
  setInput: (value: string) => void;
  notes: string;
  setNotes: (value: string) => void;
  result: AgentResponse | null;
  history: AgentRunRecord[];
  runAgent: (event: FormEvent) => Promise<void>;
}) {
  const label = mode === "product-teardown" ? "产品名" : mode === "framework-red-team" ? "项目想法" : "文章终稿";
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <form className="space-y-3" onSubmit={runAgent}>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            className={mode === "product-teardown" ? "primary-button" : "secondary-button"}
            onClick={() => setMode("product-teardown")}
          >
            初拆
          </button>
          <button
            type="button"
            className={mode === "framework-red-team" ? "primary-button" : "secondary-button"}
            onClick={() => setMode("framework-red-team")}
          >
            红队
          </button>
          <button
            type="button"
            className={mode === "article-publish-check" ? "primary-button" : "secondary-button"}
            onClick={() => setMode("article-publish-check")}
          >
            发布
          </button>
        </div>
        <label className="block text-sm font-medium">{label}</label>
        <textarea className="field min-h-44" value={input} onChange={(event) => setInput(event.target.value)} />
        <label className="block text-sm font-medium">补充信息</label>
        <textarea className="field min-h-24" value={notes} onChange={(event) => setNotes(event.target.value)} />
        <button className="primary-button w-full" type="submit">
          运行 Agent
        </button>
      </form>
      <section className="min-w-0">
        <ResultHeader title={result?.agent || "Agent 输出"} status={result?.llm?.status || result?.status} />
        <ReadFilesList files={result?.read_files ?? []} />
        <KeyValue
          rows={[
            ["结论", result?.conclusion],
            ["风险", result?.risks],
            ["最小下一步", result?.minimal_next_step],
            ["入库稿", result?.ingest_draft],
          ]}
        />
        <pre className="code-block mt-3 min-h-[360px]">
          {result?.answer_markdown || result?.answer || result?.detail || "尚未运行 Agent。"}
        </pre>
        <AgentHistory records={history} />
      </section>
    </div>
  );
}

function PatchView({
  target,
  setTarget,
  intent,
  setIntent,
  content,
  setContent,
  result,
  runPatch,
}: {
  target: string;
  setTarget: (value: string) => void;
  intent: string;
  setIntent: (value: string) => void;
  content: string;
  setContent: (value: string) => void;
  result: PatchDraftResponse | null;
  runPatch: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <form className="space-y-3" onSubmit={runPatch}>
        <label className="block text-sm font-medium">目标文件</label>
        <input className="field" value={target} onChange={(event) => setTarget(event.target.value)} />
        <label className="block text-sm font-medium">修改意图</label>
        <input className="field" value={intent} onChange={(event) => setIntent(event.target.value)} />
        <label className="block text-sm font-medium">新增内容</label>
        <textarea className="field min-h-80 font-mono" value={content} onChange={(event) => setContent(event.target.value)} />
        <button className="primary-button w-full" type="submit">
          生成入库稿
        </button>
      </form>
      <section className="min-w-0">
        <ResultHeader title={result?.suggested_save_path || "入库稿"} status={result?.operation} />
        <ReadFilesList files={result?.read_files ?? []} />
        <KeyValue
          rows={[
            ["commit", result?.commit_message],
            ["PR", result?.pr_title],
            ["说明", result?.diff_summary?.summary],
          ]}
        />
        <pre className="code-block mt-3 min-h-80">{result?.diff_preview || result?.detail || "尚未生成入库稿。"}</pre>
      </section>
    </div>
  );
}

function GraphView({
  status,
  queryKind,
  setQueryKind,
  query,
  setQuery,
  result,
  refreshStatus,
  rebuildGraph,
  runQuery,
  openFileFromGraph,
}: {
  status: GraphStatusResponse | null;
  queryKind: GraphQueryKind;
  setQueryKind: (value: GraphQueryKind) => void;
  query: string;
  setQuery: (value: string) => void;
  result: GraphQueryResponse | null;
  refreshStatus: () => Promise<void>;
  rebuildGraph: () => Promise<void>;
  runQuery: (event?: FormEvent) => Promise<void>;
  openFileFromGraph: (path: string) => Promise<void>;
}) {
  const needsInput = queryKind === "fm015" || queryKind === "framework";
  const placeholder = queryKind === "fm015" ? "FM015" : "诊断空白";
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <section>
        <form className="mb-4 space-y-3 rounded-md border border-line bg-white p-4" onSubmit={runQuery}>
          <label className="block text-sm font-medium">验收查询</label>
          <select
            className="field"
            value={queryKind}
            onChange={(event) => {
              const next = event.target.value as GraphQueryKind;
              setQueryKind(next);
              if (next === "fm015") setQuery("FM015");
              if (next === "framework") setQuery("诊断空白");
            }}
          >
            <option value="fm015">哪些案例命中 FM015？</option>
            <option value="framework">诊断空白框架出现在哪些文章？</option>
            <option value="tools">哪些产品被判为“工具”？</option>
            <option value="theories">哪些理论被多个案例引用？</option>
          </select>
          {needsInput && (
            <input
              className="field"
              value={query}
              placeholder={placeholder}
              onChange={(event) => setQuery(event.target.value)}
            />
          )}
          <button className="primary-button w-full" type="submit">
            查询图谱
          </button>
        </form>
        <div className="mb-4 grid grid-cols-2 gap-2">
          <button className="secondary-button" type="button" onClick={refreshStatus}>
            图谱状态
          </button>
          <button className="primary-button" type="button" onClick={rebuildGraph}>
            重建图谱
          </button>
        </div>
        <KeyValue
          rows={[
            ["状态", status?.status],
            ["chunk", status?.source_chunk_count],
            ["latest_index_run", status?.latest_index_run],
            ["graph_rebuild_time", status?.graph_rebuild_time],
            ["canonical", status?.canonical_read_status],
            ["节点", status?.node_count],
            ["关系", status?.relationship_count],
            ["节点类型", status?.labels],
            ["关系类型", status?.relationship_types],
          ]}
        />
      </section>
      <section className="min-w-0">
        <ResultHeader title={result?.query || "图谱查询结果"} status={result?.status} />
        <KeyValue rows={[["结果数", result?.count]]} />
        <GraphReadableResults kind={queryKind} result={result} openFile={openFileFromGraph} />
      </section>
    </div>
  );
}

function GraphReadableResults({
  kind,
  result,
  openFile,
}: {
  kind: GraphQueryKind;
  result: GraphQueryResponse | null;
  openFile: (path: string) => Promise<void>;
}) {
  if (!result) {
    return <div className="rounded-md border border-line bg-white p-4 text-sm">尚未查询图谱。</div>;
  }
  if (!result.results.length) {
    return <div className="rounded-md border border-line bg-white p-4 text-sm">没有查到结果。</div>;
  }
  return (
    <div className="space-y-3">
      {result.results.map((row, index) => (
        <GraphResultCard key={index} kind={kind} row={row} openFile={openFile} />
      ))}
    </div>
  );
}

function GraphResultCard({
  kind,
  row,
  openFile,
}: {
  kind: GraphQueryKind;
  row: Record<string, unknown>;
  openFile: (path: string) => Promise<void>;
}) {
  const title = graphResultTitle(kind, row);
  const details = graphResultDetails(kind, row);
  const filePath = typeof row.file_path === "string" ? row.file_path : "";
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="text-base font-semibold">{title}</div>
        {filePath && (
          <button className="secondary-button shrink-0" type="button" onClick={() => void openFile(filePath)}>
            阅读文件
          </button>
        )}
      </div>
      <div className="mt-3 space-y-2 text-sm text-slate-700">
        {details.map(([label, value]) => (
          <div key={label} className="grid gap-1 sm:grid-cols-[96px_1fr]">
            <div className="font-medium text-slate-500">{label}</div>
            <div className="min-w-0 break-words">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function graphResultTitle(kind: GraphQueryKind, row: Record<string, unknown>) {
  if (kind === "fm015") return String(row.case_id || row.title || "案例");
  if (kind === "framework") return String(row.article_id || row.title || "文章");
  if (kind === "tools") return String(row.product || row.product_id || "产品");
  return String(row.theory || row.theory_id || "理论");
}

function graphResultDetails(kind: GraphQueryKind, row: Record<string, unknown>): Array<[string, string]> {
  if (kind === "fm015") {
    return [
      ["标题", stringValue(row.title)],
      ["文件", stringValue(row.file_path)],
      ["行号", stringValue(row.line)],
    ];
  }
  if (kind === "framework") {
    return [
      ["标题", stringValue(row.title)],
      ["框架", stringValue(row.framework)],
      ["文件", stringValue(row.file_path)],
    ];
  }
  if (kind === "tools") {
    return [
      ["判断", stringValue(row.decision)],
      ["文件", stringValue(row.file_path)],
    ];
  }
  return [
    ["案例数", stringValue(row.case_count)],
    ["案例", Array.isArray(row.cases) ? row.cases.join("、") : stringValue(row.cases)],
  ];
}

function stringValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function MemoryView({
  registries,
  externalRuns,
  form,
  setForm,
  loadRegistries,
  loadExternalRuns,
  submitExternalRun,
}: {
  registries: MemoryRegistriesResponse | null;
  externalRuns: ExternalRunsResponse | null;
  form: ExternalRunForm;
  setForm: (value: ExternalRunForm) => void;
  loadRegistries: () => Promise<void>;
  loadExternalRuns: () => Promise<void>;
  submitExternalRun: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <section>
        <div className="mb-4 grid grid-cols-2 gap-2">
          <button className="secondary-button" type="button" onClick={loadRegistries}>
            查看分工
          </button>
          <button className="secondary-button" type="button" onClick={loadExternalRuns}>
            最近记录
          </button>
        </div>
        <form className="space-y-3 rounded-md border border-line bg-white p-4" onSubmit={submitExternalRun}>
          <h2 className="text-base font-semibold">新增 external run</h2>
          <select className="field" value={form.agent_type} onChange={(event) => setForm({ ...form, agent_type: event.target.value })}>
            <option value="chatgpt_project">ChatGPT Project</option>
            <option value="gpts">GPTS</option>
            <option value="claude">Claude</option>
            <option value="codex">Codex</option>
            <option value="hermes">Hermes</option>
            <option value="cursor">Cursor</option>
            <option value="sk_agent">sk-agent</option>
            <option value="other">Other</option>
          </select>
          <input className="field" placeholder="工具/Agent 名称" value={form.agent_name} onChange={(event) => setForm({ ...form, agent_name: event.target.value })} />
          <input className="field" placeholder="任务类型" value={form.task_type} onChange={(event) => setForm({ ...form, task_type: event.target.value })} />
          <textarea className="field min-h-24" placeholder="输入摘要" value={form.input_summary} onChange={(event) => setForm({ ...form, input_summary: event.target.value })} />
          <textarea className="field min-h-24" placeholder="输出摘要" value={form.output_summary} onChange={(event) => setForm({ ...form, output_summary: event.target.value })} />
          <input className="field" placeholder="来源链接或文件" value={form.source_link_or_file} onChange={(event) => setForm({ ...form, source_link_or_file: event.target.value })} />
          <textarea className="field min-h-20" placeholder="关联 SK 文件，一行一个" value={form.related_sk_files} onChange={(event) => setForm({ ...form, related_sk_files: event.target.value })} />
          <select className="field" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
            <option value="draft">draft</option>
            <option value="reviewed">reviewed</option>
            <option value="ingested">ingested</option>
            <option value="rejected">rejected</option>
            <option value="archived">archived</option>
          </select>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.should_ingest} onChange={(event) => setForm({ ...form, should_ingest: event.target.checked })} />
            建议入库
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.ingested} onChange={(event) => setForm({ ...form, ingested: event.target.checked })} />
            已入库
          </label>
          <textarea className="field min-h-20" placeholder="备注" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          <button className="primary-button w-full" type="submit">
            记录外部任务
          </button>
        </form>
      </section>
      <section className="min-w-0">
        <Section title="多智能体分工">
          <KeyValue
            rows={[
              ["内部 Agent", registries?.agent_registry],
              ["GPTS", registries?.gpts_registry],
              ["外部工具", registries?.external_tools],
            ]}
          />
        </Section>
        <Section title="最近 external runs">
          <div className="space-y-3">
            {(externalRuns?.runs ?? []).map((run) => (
              <div key={run.id} className="rounded-md border border-line bg-white p-4 text-sm">
                <div className="font-semibold">
                  {run.agent_name} / {run.task_type}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {formatShanghaiTime(run.created_at)} / {run.agent_type} / {run.status}
                </div>
                <p className="mt-2 leading-6 text-slate-700">{run.output_summary}</p>
                <div className="mt-2 text-xs text-slate-500">
                  should_ingest={String(run.should_ingest)} / ingested={String(run.ingested)}
                </div>
              </div>
            ))}
            {!externalRuns && <div className="rounded-md border border-line bg-white p-4 text-sm">点击“最近记录”读取。</div>}
          </div>
        </Section>
      </section>
    </div>
  );
}

function ResultHeader({ title, status }: { title: string; status?: string }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3 rounded-md border border-line bg-white px-4 py-3">
      <h2 className="truncate text-base font-semibold">{title}</h2>
      <span className="shrink-0 text-sm text-slate-600">{statusText(status)}</span>
    </div>
  );
}

function ResultList({ result, openFile }: { result: SearchResponse | null; openFile: (path: string) => Promise<void> }) {
  return (
    <div className="space-y-3">
      {(result?.results ?? []).map((hit) => (
        <div key={`${hit.file_path}-${hit.start_line}`} className="rounded-md border border-line bg-white p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="text-sm font-semibold">{hit.file_path}</div>
              <div className="mt-1 text-xs text-slate-500">
                {hit.start_line}-{hit.end_line} 行 / score {hit.total_score}
              </div>
            </div>
            <button className="secondary-button shrink-0" type="button" onClick={() => void openFile(hit.file_path)}>
              阅读文件
            </button>
          </div>
          {hit.heading && <div className="mt-2 text-sm font-medium">{hit.heading}</div>}
          <p className="mt-2 text-sm leading-6 text-slate-700">{hit.excerpt}</p>
        </div>
      ))}
      {!result && <div className="rounded-md border border-line bg-white p-4 text-sm">尚未检索。</div>}
    </div>
  );
}

function ReadFilesList({ files }: { files: ReadFileSummary[] }) {
  if (!files.length) return null;
  return (
    <div className="mt-3 rounded-md border border-line bg-white">
      <div className="border-b border-line px-3 py-2 text-sm font-semibold">已读取文件</div>
      <div className="max-h-44 overflow-auto">
        {files.map((file, index) => (
          <div key={`${file.path}-${index}`} className="border-b border-line px-3 py-2 text-sm last:border-0">
            <div className="font-medium">{file.path}</div>
            <div className="text-xs text-slate-500">
              {statusText(file.status)} / {file.source || "unknown"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentHistory({ records }: { records: AgentRunRecord[] }) {
  if (!records.length) return null;
  return (
    <div className="mt-4 rounded-md border border-line bg-white">
      <div className="border-b border-line px-3 py-2 text-sm font-semibold">最近 Agent 执行记录</div>
      <div className="max-h-72 overflow-auto">
        {records.map((record, index) => (
          <div key={`${record.time}-${index}`} className="border-b border-line px-3 py-3 text-sm last:border-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">{record.agent}</span>
              <span className="text-xs text-slate-500">{new Date(record.time).toLocaleString()}</span>
            </div>
            <div className="mt-1 line-clamp-2 text-slate-700">{record.input}</div>
            <div className="mt-2 text-slate-700">结论：{record.conclusion || "-"}</div>
            <div className="mt-1 text-xs text-slate-500">
              读取 {record.read_files.length} 个文件 / 风险 {record.risks.length} 项
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InternalRolesView({
  roles,
  runs,
  result,
  form,
  setForm,
  loadRoles,
  loadRuns,
  runRole,
}: {
  roles: RoleListResponse | null;
  runs: InternalRoleRunsResponse | null;
  result: RoleRunResponse | null;
  form: RoleRunForm;
  setForm: (value: RoleRunForm) => void;
  loadRoles: () => Promise<void>;
  loadRuns: () => Promise<void>;
  runRole: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <section>
        <div className="mb-4 grid grid-cols-2 gap-2">
          <button className="secondary-button" type="button" onClick={loadRoles}>
            查看 role 列表
          </button>
          <button className="secondary-button" type="button" onClick={loadRuns}>
            最近运行
          </button>
        </div>
        <form className="space-y-3 rounded-md border border-line bg-white p-4" onSubmit={runRole}>
          <h2 className="text-base font-semibold">运行内部角色</h2>
          <div className="rounded-md border border-line bg-panel px-3 py-2 text-sm leading-6 text-slate-700">
            联网只用于补候选证据，不会替代 SK 当前文件，不会自动入库。
          </div>
          <select className="field" value={form.task_type} onChange={(event) => setForm({ ...form, task_type: event.target.value })}>
            {Object.entries(roleTaskLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            className="field"
            placeholder="指定内部角色，可不填，系统会自动选择"
            value={form.preferred_role}
            onChange={(event) => setForm({ ...form, preferred_role: event.target.value })}
          />
          <textarea
            className="field min-h-36"
            placeholder="任务内容"
            value={form.input}
            onChange={(event) => setForm({ ...form, input: event.target.value })}
          />
          <textarea
            className="field min-h-24"
            placeholder="补充说明"
            value={form.notes}
            onChange={(event) => setForm({ ...form, notes: event.target.value })}
          />
          <label className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={form.allow_web}
              onChange={(event) => setForm({ ...form, allow_web: event.target.checked })}
            />
            允许联网补证据
          </label>
          <textarea
            className="field min-h-24"
            placeholder="可选：每行一个搜索词；留空则由角色自动生成"
            value={form.web_queries}
            onChange={(event) => setForm({ ...form, web_queries: event.target.value })}
          />
          <button className="primary-button w-full" type="submit">
            运行角色
          </button>
        </form>
        <Section title="role 列表">
          <div className="space-y-2">
            {(roles?.roles ?? []).map((role) => (
              <div key={role.role_id} className="rounded-md border border-line bg-white p-3 text-sm">
                <div className="font-semibold">{role.role_name}</div>
                <div className="text-xs text-slate-500">{role.role_id}</div>
                <p className="mt-2 leading-6 text-slate-700">{role.purpose}</p>
              </div>
            ))}
            {!roles && <div className="rounded-md border border-line bg-white p-3 text-sm">点击“查看 role 列表”。</div>}
          </div>
        </Section>
      </section>
      <section className="min-w-0">
        <ResultHeader title={result?.role_name || "内部角色输出"} status={result?.status} />
        <ReadFilesList files={result?.read_files ?? []} />
        <KeyValue
          rows={[
            ["结论", result?.conclusion],
            ["是否联网", result ? (result.web_used ? "是" : "否") : undefined],
            ["候选来源", bulletList(result?.evidence_ledger || result?.structured_output?.evidence_ledger, "暂未找到候选来源。")],
            ["缺失证据", bulletList(result?.missing_evidence || result?.structured_output?.missing_evidence, "暂未列出缺失证据。")],
            ["风险", bulletList(result?.risks, "暂未发现额外风险。")],
            ["最小下一步", result?.minimal_next_step],
          ]}
        />
        <pre className="code-block mt-3 min-h-72">
          {result?.human_readable_markdown || result?.answer_markdown || "尚未运行内部角色。"}
        </pre>
        {result && (
          <details className="mt-3 rounded-md border border-line bg-white p-3 text-sm">
            <summary className="cursor-pointer font-semibold">查看结构化输出</summary>
            <KeyValue
              rows={[
                ["搜索词", result.web_queries],
                ["warnings", result.warnings],
                ["结构化输出", result.structured_output],
              ]}
            />
          </details>
        )}
        <Section title="最近 10 次 internal_role_runs">
          <div className="space-y-3">
            {(runs?.runs ?? []).map((run) => (
              <div key={run.id} className="rounded-md border border-line bg-white p-4 text-sm">
                <div className="font-semibold">
                  {run.role_name} / {roleTaskLabels[run.task_type] || run.task_type}
                </div>
                <div className="mt-1 text-xs text-slate-500">{formatShanghaiTime(run.created_at)}</div>
                <p className="mt-2 leading-6 text-slate-700">{run.conclusion}</p>
              </div>
            ))}
            {!runs && <div className="rounded-md border border-line bg-white p-4 text-sm">点击“最近运行”读取。</div>}
          </div>
        </Section>
      </section>
    </div>
  );
}

function KeyValue({ rows }: { rows: Array<[string, unknown]> }) {
  return (
    <div className="mb-4 rounded-md border border-line bg-white">
      {rows.map(([key, value]) => (
        <div key={key} className="grid grid-cols-[120px_1fr] border-b border-line px-3 py-2 text-sm last:border-0">
          <div className="font-medium text-slate-600">{key}</div>
          <div className="min-w-0 whitespace-pre-wrap break-words">{compact(value)}</div>
        </div>
      ))}
    </div>
  );
}
