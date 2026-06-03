"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";

type ApiData = Record<string, any>;
type TabKey =
  | "cognitive"
  | "repo"
  | "index"
  | "search"
  | "audit"
  | "patch"
  | "graph"
  | "research"
  | "roles"
  | "inventory";

const tabs: Array<{ key: TabKey; label: string; hint: string }> = [
  { key: "cognitive", label: "思维流", hint: "连续判断" },
  { key: "repo", label: "仓库", hint: "文件与同步" },
  { key: "index", label: "索引", hint: "重建与状态" },
  { key: "search", label: "检索", hint: "Search / Ask" },
  { key: "audit", label: "审计", hint: "状态漂移" },
  { key: "patch", label: "入库稿", hint: "Patch Draft" },
  { key: "graph", label: "图谱", hint: "关系查询" },
  { key: "research", label: "Research State", hint: "只读状态" },
  { key: "roles", label: "Internal Roles", hint: "显式运行" },
  { key: "inventory", label: "System Inventory", hint: "系统地图" },
];

const inventoryApis = [
  "GET /repo/files",
  "GET /repo/file?path=",
  "GET /repo/canonical",
  "POST /repo/sync",
  "POST /index/rebuild",
  "GET /index/status",
  "GET /index/chunks?file_path=",
  "POST /search",
  "POST /ask",
  "POST /agents/status-audit",
  "POST /agents/product-teardown",
  "POST /agents/framework-red-team",
  "POST /agents/article-publish-check",
  "POST /patch/draft",
  "POST /graph/rebuild",
  "GET /graph/status",
  "GET /graph/failure-modes/{code}/cases",
  "GET /graph/frameworks/articles?framework=",
  "GET /graph/products/tools",
  "GET /graph/theories/reused",
  "GET /roles",
  "POST /roles/run",
  "GET /roles/runs",
  "POST /web/search",
  "POST /web/read-source",
  "GET /research/objects",
  "GET /research/objects/{slug}/state",
  "POST /cognitive/think",
  "GET /cognitive/sessions",
  "GET /cognitive/sessions/{session_id}/state",
];

const inventoryTables = [
  "files",
  "chunks",
  "index_runs",
  "external_agent_runs",
  "internal_role_runs",
  "research_objects",
  "research_sources",
  "research_facts",
  "cognitive_sessions",
  "cognitive_entities",
  "cognitive_messages",
  "cognitive_judgments",
];

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

async function fetchJson<T = ApiData>(path: string, init?: RequestInit): Promise<T> {
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

function formatTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function asList(value: unknown, fallback = "暂无") {
  if (!value) return fallback;
  if (Array.isArray(value)) {
    if (!value.length) return fallback;
    return value
      .map((item) => {
        if (typeof item === "string") return `- ${item}`;
        if (item && typeof item === "object") {
          const record = item as ApiData;
          const title = record.source_title || record.title || record.claim || record.path || record.url || record.message || "项目";
          const detail = record.evidence_level || record.status || record.source_type || "";
          return `- ${title}${detail ? `（${detail}）` : ""}`;
        }
        return `- ${String(item)}`;
      })
      .join("\n");
  }
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function compact(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("cognitive");
  const [apiDisplay, setApiDisplay] = useState("loading");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [inventoryDoc, setInventoryDoc] = useState("");

  const [health, setHealth] = useState<ApiData | null>(null);
  const [canonical, setCanonical] = useState<ApiData | null>(null);
  const [indexStatus, setIndexStatus] = useState<ApiData | null>(null);
  const [graphStatus, setGraphStatus] = useState<ApiData | null>(null);

  const [files, setFiles] = useState<ApiData | null>(null);
  const [selectedPath, setSelectedPath] = useState("README.md");
  const [fileResult, setFileResult] = useState<ApiData | null>(null);
  const [syncResult, setSyncResult] = useState<ApiData | null>(null);
  const [indexResult, setIndexResult] = useState<ApiData | null>(null);

  const [searchQuery, setSearchQuery] = useState("MTP 构思招募法在哪");
  const [searchResult, setSearchResult] = useState<ApiData | null>(null);
  const [askQuestion, setAskQuestion] = useState("诊断空白四条件是什么？");
  const [askResult, setAskResult] = useState<ApiData | null>(null);

  const [auditResult, setAuditResult] = useState<ApiData | null>(null);
  const [patchTarget, setPatchTarget] = useState("cases/2026/example.md");
  const [patchIntent, setPatchIntent] = useState("新增轻量初拆草稿");
  const [patchContent, setPatchContent] = useState("# Example\n\n正文内容");
  const [patchResult, setPatchResult] = useState<ApiData | null>(null);

  const [graphKind, setGraphKind] = useState("fm");
  const [graphQuery, setGraphQuery] = useState("FM015");
  const [graphResult, setGraphResult] = useState<ApiData | null>(null);

  const [researchObjects, setResearchObjects] = useState<ApiData | null>(null);
  const [researchSlug, setResearchSlug] = useState("");
  const [researchState, setResearchState] = useState<ApiData | null>(null);

  const [roles, setRoles] = useState<ApiData | null>(null);
  const [roleRuns, setRoleRuns] = useState<ApiData | null>(null);
  const [roleTask, setRoleTask] = useState("deep_research");
  const [roleInput, setRoleInput] = useState("研究一个产品是否值得进入 SK");
  const [roleAllowWeb, setRoleAllowWeb] = useState(false);
  const [roleReadSources, setRoleReadSources] = useState(false);
  const [roleResult, setRoleResult] = useState<ApiData | null>(null);

  const [sessionId, setSessionId] = useState("");
  const [thoughtInput, setThoughtInput] = useState("MYHAIR AI 会不会最后变成卖药渠道？");
  const [allowWeb, setAllowWeb] = useState(false);
  const [readSources, setReadSources] = useState(false);
  const [cognitiveResult, setCognitiveResult] = useState<ApiData | null>(null);
  const [cognitiveSessions, setCognitiveSessions] = useState<ApiData[]>([]);
  const flowEndRef = useRef<HTMLDivElement>(null);
  const messages = useMemo(() => cognitiveResult?.messages ?? [], [cognitiveResult]);

  useEffect(() => {
    setApiDisplay(apiBaseUrl());
    void refreshSystemStatus();
    void loadCognitiveSessions();
  }, []);

  useEffect(() => {
    flowEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  useEffect(() => {
    if (activeTab === "inventory" && !inventoryDoc) void loadInventoryDoc();
  }, [activeTab, inventoryDoc]);

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

  async function refreshSystemStatus() {
    await run("刷新系统状态", async () => {
      const [healthPayload, canonicalPayload, indexPayload, graphPayload] = await Promise.allSettled([
        fetchJson("/health"),
        fetchJson("/repo/canonical"),
        fetchJson("/index/status"),
        fetchJson("/graph/status"),
      ]);
      if (healthPayload.status === "fulfilled") setHealth(healthPayload.value);
      if (canonicalPayload.status === "fulfilled") setCanonical(canonicalPayload.value);
      if (indexPayload.status === "fulfilled") setIndexStatus(indexPayload.value);
      if (graphPayload.status === "fulfilled") setGraphStatus(graphPayload.value);
      return true;
    });
  }

  async function syncRepo() {
    const result = await run("同步仓库", () => fetchJson("/repo/sync", { method: "POST", body: "{}" }));
    if (result) {
      setSyncResult(result);
      await refreshSystemStatus();
    }
  }

  async function rebuildIndex() {
    const result = await run("重建索引", () => fetchJson("/index/rebuild", { method: "POST", body: "{}" }));
    if (result) {
      setIndexResult(result);
      setIndexStatus(result);
    }
  }

  async function runStatusAudit() {
    const result = await run("状态审计", () => fetchJson("/agents/status-audit", { method: "POST", body: "{}" }));
    if (result) setAuditResult(result);
  }

  async function rebuildGraph() {
    const result = await run("重建图谱", () => fetchJson("/graph/rebuild", { method: "POST", body: "{}" }));
    if (result) setGraphStatus(result);
  }

  async function loadRepoFiles() {
    const result = await run("读取文件树", () => fetchJson("/repo/files"));
    if (result) setFiles(result);
  }

  async function readRepoFile(path = selectedPath) {
    const result = await run("读取文件", () => fetchJson(`/repo/file?path=${encodeURIComponent(path)}`));
    if (result) {
      setSelectedPath(path);
      setFileResult(result);
    }
  }

  async function refreshCanonical() {
    const result = await run("读取 canonical files", () => fetchJson("/repo/canonical"));
    if (result) setCanonical(result);
  }

  async function refreshIndexStatus() {
    const result = await run("读取索引状态", () => fetchJson("/index/status"));
    if (result) setIndexStatus(result);
  }

  async function runSearch(event?: FormEvent) {
    event?.preventDefault();
    const result = await run("检索", () =>
      fetchJson("/search", { method: "POST", body: JSON.stringify({ query: searchQuery, limit: 8 }) }),
    );
    if (result) setSearchResult(result);
  }

  async function runAsk(event?: FormEvent) {
    event?.preventDefault();
    const result = await run("问答", () =>
      fetchJson("/ask", { method: "POST", body: JSON.stringify({ question: askQuestion, limit: 6 }) }),
    );
    if (result) setAskResult(result);
  }

  async function runPatch(event: FormEvent) {
    event.preventDefault();
    const result = await run("生成入库稿", () =>
      fetchJson("/patch/draft", {
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
    const result = await run("读取图谱状态", () => fetchJson("/graph/status"));
    if (result) setGraphStatus(result);
  }

  async function runGraphQuery(event?: FormEvent) {
    event?.preventDefault();
    const endpoint =
      graphKind === "fm"
        ? `/graph/failure-modes/${encodeURIComponent(graphQuery || "FM015")}/cases`
        : graphKind === "framework"
          ? `/graph/frameworks/articles?framework=${encodeURIComponent(graphQuery || "诊断空白")}`
          : graphKind === "tools"
            ? "/graph/products/tools"
            : "/graph/theories/reused";
    const result = await run("图谱查询", () => fetchJson(endpoint));
    if (result) setGraphResult(result);
  }

  async function loadResearchObjects() {
    const result = await run("读取 Research State", () => fetchJson("/research/objects?limit=50"));
    if (result) {
      setResearchObjects(result);
      const first = result.objects?.[0]?.slug;
      if (!researchSlug && first) setResearchSlug(first);
    }
  }

  async function loadResearchState(slug = researchSlug) {
    if (!slug) return;
    const result = await run("读取研究状态", () => fetchJson(`/research/objects/${encodeURIComponent(slug)}/state`));
    if (result) {
      setResearchSlug(slug);
      setResearchState(result.state ?? result);
    }
  }

  async function loadRoles() {
    const result = await run("读取角色", () => fetchJson("/roles"));
    if (result) setRoles(result);
  }

  async function loadRoleRuns() {
    const result = await run("读取角色运行记录", () => fetchJson("/roles/runs?limit=10"));
    if (result) setRoleRuns(result);
  }

  async function runRole(event: FormEvent) {
    event.preventDefault();
    const result = await run("运行内部角色", () =>
      fetchJson("/roles/run", {
        method: "POST",
        body: JSON.stringify({
          task_type: roleTask,
          input: roleInput,
          allow_web: roleAllowWeb,
          read_sources: roleReadSources,
        }),
      }),
    );
    if (result) {
      setRoleResult(result);
      await loadRoleRuns();
    }
  }

  async function loadCognitiveSessions() {
    try {
      const payload = await fetchJson("/cognitive/sessions?limit=10");
      setCognitiveSessions(payload.sessions ?? []);
    } catch {
      setCognitiveSessions([]);
    }
  }

  async function loadInventoryDoc() {
    try {
      const response = await fetch("/api/system-inventory");
      const payload = await response.json();
      if (payload.status === "ok") setInventoryDoc(payload.markdown ?? "");
    } catch {
      setInventoryDoc("");
    }
  }

  async function think(event: FormEvent) {
    event.preventDefault();
    const result = await run("继续思考", () =>
      fetchJson("/cognitive/think", {
        method: "POST",
        body: JSON.stringify({
          input: thoughtInput,
          session_id: sessionId || undefined,
          allow_web: allowWeb,
          read_sources: readSources,
        }),
      }),
    );
    if (result) {
      setCognitiveResult(result);
      setSessionId(result.session?.id ?? "");
      setThoughtInput("");
      await loadCognitiveSessions();
    }
  }

  async function openCognitiveSession(id: string) {
    const result = await run("打开思维流", () => fetchJson(`/cognitive/sessions/${encodeURIComponent(id)}/state`));
    if (result) {
      setSessionId(id);
      setCognitiveResult({
        ...result,
        current_topic: result.session?.current_topic,
        current_judgment: result.session?.cognitive_state?.current_judgment,
        why: result.session?.cognitive_state?.why,
        evidence: result.session?.cognitive_state?.evidence ?? [],
        risks: result.session?.cognitive_state?.risks ?? [],
        unresolved_questions: result.session?.cognitive_state?.unresolved_questions ?? [],
        next_question: result.session?.cognitive_state?.next_question,
      });
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-slate-900">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-xl font-semibold">SK Agent Workbench</h1>
            <p className="mt-1 text-sm text-slate-600">系统控制台已恢复：Cognitive Flow 是一个模式，不再覆盖全部工作台。</p>
          </div>
          <div className="rounded-md border border-line bg-panel px-3 py-2 text-xs text-slate-600">API: {apiDisplay}</div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-5 py-5 lg:grid-cols-[230px_minmax(0,1fr)_300px]">
        <nav className="space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                activeTab === tab.key ? "border-accent bg-white text-accent" : "border-line bg-white text-slate-700 hover:border-accent"
              }`}
              type="button"
              onClick={() => setActiveTab(tab.key)}
            >
              <div className="font-medium">{tab.label}</div>
              <div className="mt-1 text-xs text-slate-500">{tab.hint}</div>
            </button>
          ))}
        </nav>

        <section className="min-w-0">
          {error && <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          {busy && <div className="mb-4 rounded-md border border-line bg-white px-4 py-3 text-sm text-slate-600">正在执行：{busy}</div>}
          {activeTab === "cognitive" && (
            <CognitiveView
              sessionId={sessionId}
              setSessionId={setSessionId}
              input={thoughtInput}
              setInput={setThoughtInput}
              allowWeb={allowWeb}
              setAllowWeb={setAllowWeb}
              readSources={readSources}
              setReadSources={setReadSources}
              result={cognitiveResult}
              sessions={cognitiveSessions}
              submit={think}
              openSession={openCognitiveSession}
              flowEndRef={flowEndRef}
              busy={Boolean(busy)}
            />
          )}
          {activeTab === "repo" && (
            <RepoView
              files={files}
              selectedPath={selectedPath}
              setSelectedPath={setSelectedPath}
              fileResult={fileResult}
              canonical={canonical}
              syncResult={syncResult}
              loadFiles={loadRepoFiles}
              readFile={readRepoFile}
              refreshCanonical={refreshCanonical}
              syncRepo={syncRepo}
            />
          )}
          {activeTab === "index" && (
            <IndexView status={indexStatus} result={indexResult} refreshStatus={refreshIndexStatus} rebuildIndex={rebuildIndex} />
          )}
          {activeTab === "search" && (
            <SearchView
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              searchResult={searchResult}
              runSearch={runSearch}
              askQuestion={askQuestion}
              setAskQuestion={setAskQuestion}
              askResult={askResult}
              runAsk={runAsk}
              openFile={(path) => {
                setActiveTab("repo");
                void readRepoFile(path);
              }}
            />
          )}
          {activeTab === "audit" && <AuditView result={auditResult} runAudit={runStatusAudit} />}
          {activeTab === "patch" && (
            <PatchView
              target={patchTarget}
              setTarget={setPatchTarget}
              intent={patchIntent}
              setIntent={setPatchIntent}
              content={patchContent}
              setContent={setPatchContent}
              result={patchResult}
              submit={runPatch}
            />
          )}
          {activeTab === "graph" && (
            <GraphView
              status={graphStatus}
              kind={graphKind}
              setKind={setGraphKind}
              query={graphQuery}
              setQuery={setGraphQuery}
              result={graphResult}
              refreshStatus={refreshGraphStatus}
              rebuildGraph={rebuildGraph}
              runQuery={runGraphQuery}
            />
          )}
          {activeTab === "research" && (
            <ResearchView
              objects={researchObjects}
              slug={researchSlug}
              setSlug={setResearchSlug}
              state={researchState}
              loadObjects={loadResearchObjects}
              loadState={loadResearchState}
            />
          )}
          {activeTab === "roles" && (
            <RolesView
              roles={roles}
              runs={roleRuns}
              task={roleTask}
              setTask={setRoleTask}
              input={roleInput}
              setInput={setRoleInput}
              allowWeb={roleAllowWeb}
              setAllowWeb={setRoleAllowWeb}
              readSources={roleReadSources}
              setReadSources={setRoleReadSources}
              result={roleResult}
              loadRoles={loadRoles}
              loadRuns={loadRoleRuns}
              runRole={runRole}
            />
          )}
          {activeTab === "inventory" && <InventoryView markdown={inventoryDoc} reload={loadInventoryDoc} />}
        </section>

        <SystemStatus
          health={health}
          canonical={canonical}
          indexStatus={indexStatus}
          graphStatus={graphStatus}
          refresh={refreshSystemStatus}
          syncRepo={syncRepo}
          rebuildIndex={rebuildIndex}
          runStatusAudit={runStatusAudit}
          rebuildGraph={rebuildGraph}
        />
      </div>
    </main>
  );
}

function CognitiveView(props: {
  sessionId: string;
  setSessionId: (value: string) => void;
  input: string;
  setInput: (value: string) => void;
  allowWeb: boolean;
  setAllowWeb: (value: boolean) => void;
  readSources: boolean;
  setReadSources: (value: boolean) => void;
  result: ApiData | null;
  sessions: ApiData[];
  submit: (event: FormEvent) => Promise<void>;
  openSession: (id: string) => Promise<void>;
  flowEndRef: RefObject<HTMLDivElement>;
  busy: boolean;
}) {
  const messages = props.result?.messages ?? [];
  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
      <Panel title="思维流">
        <button className="secondary-button mb-3 w-full" type="button" onClick={() => props.setSessionId("")}>
          新思路
        </button>
        <div className="space-y-2">
          {props.sessions.map((session) => (
            <button
              key={session.id}
              className="w-full rounded-md border border-line bg-white p-3 text-left text-sm hover:border-accent"
              type="button"
              onClick={() => props.openSession(session.id)}
            >
              <div className="font-medium">{session.current_topic || session.title || "未命名"}</div>
              <div className="mt-1 text-xs text-slate-500">{formatTime(session.updated_at)}</div>
            </button>
          ))}
        </div>
      </Panel>
      <div className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <div className="font-semibold">{props.result?.current_topic || "连续思考流"}</div>
          <div className="mt-1 text-xs text-slate-500">Session: {props.sessionId || "新会话"}</div>
        </div>
        <div className="max-h-[560px] space-y-4 overflow-auto p-4">
          {messages.map((message: ApiData) => (
            <div key={message.id} className={message.role === "user" ? "ml-auto max-w-[82%]" : "mr-auto max-w-[88%]"}>
              <div className={message.role === "user" ? "rounded-md bg-accent px-4 py-3 text-sm leading-6 text-white" : "rounded-md border border-line bg-panel px-4 py-3 text-sm leading-6"}>
                <div className="mb-1 text-xs opacity-70">{message.role === "user" ? "你" : "SK Agent"} / {formatTime(message.created_at)}</div>
                <pre className="whitespace-pre-wrap break-words font-sans">{message.content}</pre>
              </div>
            </div>
          ))}
          <div ref={props.flowEndRef} />
          {!messages.length && <div className="rounded-md border border-line bg-panel p-4 text-sm">直接输入你的想法，系统会在同一思维流里延续判断。</div>}
        </div>
        <form className="border-t border-line p-4" onSubmit={props.submit}>
          <textarea className="field min-h-24" value={props.input} onChange={(event) => props.setInput(event.target.value)} placeholder="直接说你的想法、追问、怀疑或联想..." />
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-3 text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={props.allowWeb} onChange={(event) => props.setAllowWeb(event.target.checked)} />
                允许联网补证据
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={props.readSources} onChange={(event) => props.setReadSources(event.target.checked)} />
                读取重点来源正文
              </label>
            </div>
            <button className="primary-button" type="submit" disabled={props.busy || !props.input.trim()}>
              继续思考
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RepoView(props: {
  files: ApiData | null;
  selectedPath: string;
  setSelectedPath: (value: string) => void;
  fileResult: ApiData | null;
  canonical: ApiData | null;
  syncResult: ApiData | null;
  loadFiles: () => Promise<void>;
  readFile: (path?: string) => Promise<void>;
  refreshCanonical: () => Promise<void>;
  syncRepo: () => Promise<void>;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <section className="space-y-4">
        <Panel title="仓库操作">
          <div className="grid grid-cols-2 gap-2">
            <button className="secondary-button" type="button" onClick={props.syncRepo}>Sync Repo</button>
            <button className="secondary-button" type="button" onClick={props.refreshCanonical}>Canonical</button>
            <button className="secondary-button" type="button" onClick={props.loadFiles}>文件树</button>
            <button className="secondary-button" type="button" onClick={() => props.readFile()}>读取文件</button>
          </div>
          {props.syncResult && <pre className="code-block mt-3 max-h-40">{JSON.stringify(props.syncResult, null, 2)}</pre>}
        </Panel>
        <Panel title="文件树">
          <div className="max-h-[560px] space-y-1 overflow-auto">
            {(props.files?.files ?? []).map((file: ApiData) => (
              <button key={file.path} className="block w-full truncate rounded border border-transparent px-2 py-1 text-left text-sm hover:border-line hover:bg-panel" type="button" onClick={() => props.readFile(file.path)}>
                {file.path}
              </button>
            ))}
            {!props.files && <p className="text-sm text-slate-600">点击“文件树”加载。</p>}
          </div>
        </Panel>
      </section>
      <section className="space-y-4">
        <Panel title="读取文件">
          <div className="flex gap-2">
            <input className="field" value={props.selectedPath} onChange={(event) => props.setSelectedPath(event.target.value)} />
            <button className="primary-button shrink-0" type="button" onClick={() => props.readFile()}>读取</button>
          </div>
          <pre className="code-block mt-3 min-h-96">{props.fileResult?.content || JSON.stringify(props.fileResult ?? {}, null, 2)}</pre>
        </Panel>
        <Panel title="Canonical Files">
          <pre className="code-block max-h-96">{JSON.stringify(props.canonical ?? {}, null, 2)}</pre>
        </Panel>
      </section>
    </div>
  );
}

function IndexView({ status, result, refreshStatus, rebuildIndex }: { status: ApiData | null; result: ApiData | null; refreshStatus: () => Promise<void>; rebuildIndex: () => Promise<void> }) {
  return (
    <div className="space-y-4">
      <Panel title="索引操作">
        <div className="flex flex-wrap gap-2">
          <button className="secondary-button" type="button" onClick={refreshStatus}>读取索引状态</button>
          <button className="primary-button" type="button" onClick={rebuildIndex}>Rebuild Index</button>
        </div>
      </Panel>
      <Panel title="索引状态">
        <pre className="code-block">{JSON.stringify(result ?? status ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function SearchView(props: {
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchResult: ApiData | null;
  runSearch: (event?: FormEvent) => Promise<void>;
  askQuestion: string;
  setAskQuestion: (value: string) => void;
  askResult: ApiData | null;
  runAsk: (event?: FormEvent) => Promise<void>;
  openFile: (path: string) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Keyword Search">
        <form onSubmit={props.runSearch}>
          <textarea className="field min-h-24" value={props.searchQuery} onChange={(event) => props.setSearchQuery(event.target.value)} />
          <button className="primary-button mt-3" type="submit">搜索</button>
        </form>
        <div className="mt-4 space-y-2">
          {(props.searchResult?.results ?? []).map((hit: ApiData) => (
            <div key={`${hit.file_path}-${hit.start_line}`} className="rounded-md border border-line p-3 text-sm">
              <button className="font-semibold text-accent" type="button" onClick={() => props.openFile(hit.file_path)}>{hit.file_path}</button>
              <div className="mt-1 text-xs text-slate-500">{hit.start_line}-{hit.end_line}</div>
              <p className="mt-2 leading-6">{hit.excerpt}</p>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Ask Workspace">
        <form onSubmit={props.runAsk}>
          <textarea className="field min-h-24" value={props.askQuestion} onChange={(event) => props.setAskQuestion(event.target.value)} />
          <button className="primary-button mt-3" type="submit">问答</button>
        </form>
        <pre className="code-block mt-4 min-h-96">{props.askResult?.answer_markdown || props.askResult?.answer || JSON.stringify(props.askResult ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function AuditView({ result, runAudit }: { result: ApiData | null; runAudit: () => Promise<void> }) {
  return (
    <div className="space-y-4">
      <Panel title="Status Audit">
        <button className="primary-button" type="button" onClick={runAudit}>Run Status Audit</button>
      </Panel>
      <Panel title="审计结果">
        <KeyValue rows={[["结论", result?.conclusion], ["风险等级", result?.risk_level], ["最小修复", asList(result?.minimal_fix_plan)], ["冲突", asList(result?.conflicts)], ["已读文件", asList(result?.read_files)]]} />
        <pre className="code-block mt-3">{result?.answer_markdown || JSON.stringify(result ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function PatchView(props: {
  target: string;
  setTarget: (value: string) => void;
  intent: string;
  setIntent: (value: string) => void;
  content: string;
  setContent: (value: string) => void;
  result: ApiData | null;
  submit: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <form className="space-y-3 rounded-md border border-line bg-white p-4" onSubmit={props.submit}>
        <h2 className="font-semibold">Patch Draft</h2>
        <input className="field" value={props.target} onChange={(event) => props.setTarget(event.target.value)} placeholder="目标文件" />
        <input className="field" value={props.intent} onChange={(event) => props.setIntent(event.target.value)} placeholder="修改意图" />
        <textarea className="field min-h-72" value={props.content} onChange={(event) => props.setContent(event.target.value)} />
        <button className="primary-button w-full" type="submit">生成入库稿</button>
      </form>
      <Panel title="入库稿结果">
        <KeyValue rows={[["保存路径", props.result?.suggested_save_path], ["commit", props.result?.commit_message], ["PR title", props.result?.pr_title], ["风险", asList(props.result?.risk_notes)]]} />
        <pre className="code-block mt-3 min-h-96">{props.result?.markdown_body || JSON.stringify(props.result ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function GraphView(props: {
  status: ApiData | null;
  kind: string;
  setKind: (value: string) => void;
  query: string;
  setQuery: (value: string) => void;
  result: ApiData | null;
  refreshStatus: () => Promise<void>;
  rebuildGraph: () => Promise<void>;
  runQuery: (event?: FormEvent) => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      <Panel title="Graph 操作">
        <div className="flex flex-wrap gap-2">
          <button className="secondary-button" type="button" onClick={props.refreshStatus}>Graph Status</button>
          <button className="primary-button" type="button" onClick={props.rebuildGraph}>Rebuild Graph</button>
        </div>
      </Panel>
      <Panel title="Graph 查询">
        <form className="flex flex-col gap-2 sm:flex-row" onSubmit={props.runQuery}>
          <select className="field sm:w-52" value={props.kind} onChange={(event) => props.setKind(event.target.value)}>
            <option value="fm">Failure Mode Cases</option>
            <option value="framework">Framework Articles</option>
            <option value="tools">Tool Products</option>
            <option value="theories">Reused Theories</option>
          </select>
          <input className="field" value={props.query} onChange={(event) => props.setQuery(event.target.value)} />
          <button className="primary-button shrink-0" type="submit">查询</button>
        </form>
      </Panel>
      <Panel title="Graph 结果">
        <pre className="code-block">{JSON.stringify(props.result ?? props.status ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function ResearchView(props: {
  objects: ApiData | null;
  slug: string;
  setSlug: (value: string) => void;
  state: ApiData | null;
  loadObjects: () => Promise<void>;
  loadState: (slug?: string) => Promise<void>;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
      <Panel title="Research Objects">
        <button className="secondary-button mb-3 w-full" type="button" onClick={props.loadObjects}>读取对象</button>
        <div className="space-y-2">
          {(props.objects?.objects ?? []).map((item: ApiData) => (
            <button key={item.slug} className="w-full rounded-md border border-line p-3 text-left text-sm hover:border-accent" type="button" onClick={() => props.loadState(item.slug)}>
              <div className="font-semibold">{item.name}</div>
              <div className="mt-1 text-xs text-slate-500">{item.slug} / sources {item.source_count ?? 0} / facts {item.fact_count ?? 0}</div>
            </button>
          ))}
        </div>
      </Panel>
      <Panel title="Research State 只读">
        <div className="flex gap-2">
          <input className="field" value={props.slug} onChange={(event) => props.setSlug(event.target.value)} placeholder="slug" />
          <button className="primary-button shrink-0" type="button" onClick={() => props.loadState()}>读取</button>
        </div>
        <KeyValue rows={[["对象", props.state?.object?.name], ["来源数", props.state?.counts?.sources], ["已读来源", props.state?.counts?.read_sources], ["事实数", props.state?.counts?.facts], ["缺口", asList(props.state?.gaps)], ["风险", asList(props.state?.risks)], ["下一步", asList(props.state?.next_actions)]]} />
        <pre className="code-block mt-3 max-h-[520px]">{JSON.stringify(props.state ?? {}, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function RolesView(props: {
  roles: ApiData | null;
  runs: ApiData | null;
  task: string;
  setTask: (value: string) => void;
  input: string;
  setInput: (value: string) => void;
  allowWeb: boolean;
  setAllowWeb: (value: boolean) => void;
  readSources: boolean;
  setReadSources: (value: boolean) => void;
  result: ApiData | null;
  loadRoles: () => Promise<void>;
  loadRuns: () => Promise<void>;
  runRole: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <section className="space-y-4">
        <Panel title="Internal Roles">
          <div className="grid grid-cols-2 gap-2">
            <button className="secondary-button" type="button" onClick={props.loadRoles}>角色列表</button>
            <button className="secondary-button" type="button" onClick={props.loadRuns}>运行记录</button>
          </div>
        </Panel>
        <form className="space-y-3 rounded-md border border-line bg-white p-4" onSubmit={props.runRole}>
          <select className="field" value={props.task} onChange={(event) => props.setTask(event.target.value)}>
            <option value="deep_research">deep_research</option>
            <option value="product_teardown">product_teardown</option>
            <option value="first_reader">first_reader</option>
            <option value="writing_workshop">writing_workshop</option>
            <option value="repo_governance">repo_governance</option>
            <option value="patch_draft">patch_draft</option>
            <option value="article_publish_check">article_publish_check</option>
          </select>
          <textarea className="field min-h-40" value={props.input} onChange={(event) => props.setInput(event.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={props.allowWeb} onChange={(event) => props.setAllowWeb(event.target.checked)} />
            允许联网
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={props.readSources} onChange={(event) => props.setReadSources(event.target.checked)} />
            读取来源正文
          </label>
          <button className="primary-button w-full" type="submit">运行角色</button>
        </form>
      </section>
      <section className="space-y-4">
        <Panel title="角色输出">
          <KeyValue rows={[["role", props.result?.role_name], ["结论", props.result?.conclusion], ["风险", asList(props.result?.risks)], ["下一步", props.result?.minimal_next_step]]} />
          <pre className="code-block mt-3 max-h-96">{props.result?.human_readable_markdown || props.result?.answer_markdown || JSON.stringify(props.result ?? {}, null, 2)}</pre>
        </Panel>
        <Panel title="角色列表 / 运行记录">
          <pre className="code-block max-h-96">{JSON.stringify(props.roles ?? props.runs ?? {}, null, 2)}</pre>
        </Panel>
      </section>
    </div>
  );
}

function InventoryView({ markdown, reload }: { markdown: string; reload: () => Promise<void> }) {
  return (
    <div className="space-y-4">
      <Panel title="System Inventory">
        <p className="text-sm leading-7 text-slate-700">
          来源：<code>docs/system-inventory-audit.md</code>。当前页面通过前端只读接口读取这份报告。
        </p>
        <button className="secondary-button mt-3" type="button" onClick={reload}>重新读取报告</button>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="当前 API">
          <pre className="code-block max-h-96">{inventoryApis.join("\n")}</pre>
        </Panel>
        <Panel title="当前数据库表">
          <pre className="code-block max-h-96">{inventoryTables.join("\n")}</pre>
        </Panel>
      </div>
      <Panel title="模块状态">
        <KeyValue
          rows={[
            ["当前首页模式", "SK Agent Workbench；Cognitive Flow 已降级为导航中的一个模式"],
            ["必须保留", "Repo / Index / Search / Ask / Status Audit / Patch / Roles / Research / Cognitive"],
            ["可选保留", "Graph / Memory / SKGPT / LLM debug"],
            ["已恢复可见", "Sync Repo / Rebuild Index / Run Status Audit / Rebuild Graph / Internal Roles / Research State"],
            ["仍未新增", "agent_runs / conversations / conversation_messages / autonomous agent"],
          ]}
        />
      </Panel>
      <Panel title="审计报告原文">
        <pre className="code-block max-h-[640px]">{markdown || "未读取到 docs/system-inventory-audit.md"}</pre>
      </Panel>
    </div>
  );
}

function SystemStatus(props: {
  health: ApiData | null;
  canonical: ApiData | null;
  indexStatus: ApiData | null;
  graphStatus: ApiData | null;
  refresh: () => Promise<void>;
  syncRepo: () => Promise<void>;
  rebuildIndex: () => Promise<void>;
  runStatusAudit: () => Promise<void>;
  rebuildGraph: () => Promise<void>;
}) {
  return (
    <aside className="space-y-4">
      <Panel title="系统状态">
        <KeyValue
          rows={[
            ["health", props.health?.status],
            ["canonical", `${props.canonical?.read_count ?? "-"} / ${props.canonical?.total ?? "-"}`],
            ["index files", props.indexStatus?.file_count],
            ["chunks", props.indexStatus?.chunk_count],
            ["graph nodes", props.graphStatus?.node_count],
            ["graph rels", props.graphStatus?.relationship_count],
          ]}
        />
        <button className="secondary-button mt-3 w-full" type="button" onClick={props.refresh}>刷新状态</button>
      </Panel>
      <Panel title="运维入口">
        <div className="grid gap-2">
          <button className="secondary-button" type="button" onClick={props.syncRepo}>Sync Repo</button>
          <button className="secondary-button" type="button" onClick={props.rebuildIndex}>Rebuild Index</button>
          <button className="secondary-button" type="button" onClick={props.runStatusAudit}>Run Status Audit</button>
          <button className="secondary-button" type="button" onClick={props.rebuildGraph}>Rebuild Graph</button>
        </div>
      </Panel>
      <Panel title="安全边界">
        <ul className="space-y-2 text-sm leading-6 text-slate-700">
          <li>不自动写 SK 仓库</li>
          <li>不自动 commit / push / PR</li>
          <li>联网结果只是候选证据</li>
          <li>canonical files 仍是最高优先级</li>
        </ul>
      </Panel>
    </aside>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function KeyValue({ rows }: { rows: Array<[string, unknown]> }) {
  return (
    <div className="rounded-md border border-line bg-white">
      {rows.map(([key, value]) => (
        <div key={key} className="grid grid-cols-[96px_1fr] border-b border-line px-3 py-2 text-sm last:border-0">
          <div className="font-medium text-slate-500">{key}</div>
          <div className="min-w-0 whitespace-pre-wrap break-words">{compact(value)}</div>
        </div>
      ))}
    </div>
  );
}
