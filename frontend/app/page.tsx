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
  read_files?: ReadFileSummary[];
  answer?: string;
  llm?: { status?: string; provider?: string; model?: string; message?: string };
  ingest_recommendation?: Record<string, unknown>;
  search?: { count?: number; read_files?: string[] };
  detail?: string;
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
  source_chunk_count?: number;
  detail?: string;
};

type GraphQueryResponse = {
  status: string;
  query: string;
  count: number;
  results: Array<Record<string, unknown>>;
  detail?: string;
};

type TabKey = "home" | "files" | "search" | "audit" | "agents" | "patch" | "graph";
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
];

const canonicalPaths = [
  "README.md",
  "ops/执行状态总表.md",
  "cases/2026/case-index.md",
  "cases/2026/case-cards.md",
];

const quickSearches = ["MTP 构思招募法在哪", "诊断空白四条件是什么", "failure_modes", "产品评估决策清单"];

function apiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
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

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [health, setHealth] = useState<"ok" | "offline">("offline");
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
  const [patchTarget, setPatchTarget] = useState("cases/2026/example.md");
  const [patchIntent, setPatchIntent] = useState("新增轻量初拆文档");
  const [patchContent, setPatchContent] = useState("# Example\n\n正文内容");
  const [patchResult, setPatchResult] = useState<PatchDraftResponse | null>(null);
  const [graphStatus, setGraphStatus] = useState<GraphStatusResponse | null>(null);
  const [graphQueryKind, setGraphQueryKind] = useState<GraphQueryKind>("fm015");
  const [graphQuery, setGraphQuery] = useState("FM015");
  const [graphResult, setGraphResult] = useState<GraphQueryResponse | null>(null);
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState<string>("");

  const canonicalByPath = useMemo(() => {
    return new Map((canonical?.files ?? []).map((item) => [item.path, item]));
  }, [canonical]);

  useEffect(() => {
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
    if (result) setAgentResult(result);
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

  return (
    <main className="min-h-screen bg-panel text-ink">
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
              <Metric label="API" value={apiBaseUrl()} />
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
          />
        )}
      </div>
    </main>
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
                  <td className="px-4 py-3 text-slate-600">{meta?.last_modified ?? "-"}</td>
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
}: {
  query: string;
  setQuery: (value: string) => void;
  result: SearchResponse | null;
  runSearch: (query?: string) => Promise<void>;
  askQuestion: string;
  setAskQuestion: (value: string) => void;
  askResult: AskResponse | null;
  runAsk: (event?: FormEvent) => Promise<void>;
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
        <ResultList result={result} />
      </section>
      <section>
        <form className="mb-3 flex gap-2" onSubmit={runAsk}>
          <input className="field" value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} />
          <button className="primary-button" type="submit">
            问答
          </button>
        </form>
        <ReadFilesList files={askResult?.read_files ?? []} />
        <pre className="code-block mt-3 min-h-80">{askResult?.answer || askResult?.detail || "尚未运行问答。"}</pre>
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
  runAgent,
}: {
  mode: AgentMode;
  setMode: (value: AgentMode) => void;
  input: string;
  setInput: (value: string) => void;
  notes: string;
  setNotes: (value: string) => void;
  result: AgentResponse | null;
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
        <pre className="code-block mt-3 min-h-[520px]">{result?.answer || result?.detail || "尚未运行 Agent。"}</pre>
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
}) {
  const needsInput = queryKind === "fm015" || queryKind === "framework";
  const placeholder = queryKind === "fm015" ? "FM015" : "诊断空白";
  return (
    <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
      <section>
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
            ["节点", status?.node_count],
            ["关系", status?.relationship_count],
            ["节点类型", status?.labels],
            ["关系类型", status?.relationship_types],
          ]}
        />
        <form className="space-y-3" onSubmit={runQuery}>
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
      </section>
      <section className="min-w-0">
        <ResultHeader title={result?.query || "图谱查询结果"} status={result?.status} />
        <KeyValue rows={[["结果数", result?.count]]} />
        <pre className="code-block min-h-[520px]">
          {result ? JSON.stringify(result.results, null, 2) : "尚未查询图谱。"}
        </pre>
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

function ResultList({ result }: { result: SearchResponse | null }) {
  return (
    <div className="space-y-3">
      {(result?.results ?? []).map((hit) => (
        <div key={`${hit.file_path}-${hit.start_line}`} className="rounded-md border border-line bg-white p-4">
          <div className="text-sm font-semibold">{hit.file_path}</div>
          <div className="mt-1 text-xs text-slate-500">
            {hit.start_line}-{hit.end_line} · score {hit.total_score}
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
