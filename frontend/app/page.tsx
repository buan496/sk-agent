type FileReadResult = {
  status: string;
  path?: string;
  message?: string;
  file?: {
    path: string;
    size: number;
    last_modified: string | null;
    source: string;
  } | null;
};

type CanonicalResponse = {
  status: string;
  read_count: number;
  total: number;
  files: FileReadResult[];
};

type BackendSnapshot = {
  apiBaseUrl: string;
  health: "ok" | "offline";
  canonical: CanonicalResponse | null;
};

const canonicalPaths = [
  "README.md",
  "ops/执行状态总表.md",
  "cases/2026/case-index.md",
  "cases/2026/case-cards.md",
];

async function getJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function loadBackendSnapshot(): Promise<BackendSnapshot> {
  const publicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const serverApiBaseUrl = process.env.INTERNAL_API_BASE_URL ?? publicApiBaseUrl;
  const health = await getJson<{ status?: string }>(`${serverApiBaseUrl}/health`);
  const canonical = await getJson<CanonicalResponse>(`${serverApiBaseUrl}/repo/canonical`);

  return {
    apiBaseUrl: publicApiBaseUrl,
    health: health?.status === "ok" ? "ok" : "offline",
    canonical,
  };
}

function statusLabel(status: string) {
  if (status === "ok") return "已读取";
  if (status === "not_found") return "本次未读取到";
  if (status === "not_configured") return "未配置";
  return status;
}

export default async function Home() {
  const snapshot = await loadBackendSnapshot();
  const filesByPath = new Map(snapshot.canonical?.files.map((item) => [item.path, item]) ?? []);

  return (
    <main className="min-h-screen bg-panel text-ink">
      <section className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 px-6 py-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-medium text-accent">Local-first repository reader</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal">SK Agent 工作台</h1>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-md border border-line bg-panel px-4 py-3">
              <div className="text-xs uppercase text-slate-500">Backend</div>
              <div className="mt-1 font-semibold">{snapshot.health === "ok" ? "ok" : "offline"}</div>
            </div>
            <div className="rounded-md border border-line bg-panel px-4 py-3">
              <div className="text-xs uppercase text-slate-500">Canonical</div>
              <div className="mt-1 font-semibold">
                {snapshot.canonical ? `${snapshot.canonical.read_count}/${snapshot.canonical.total}` : "0/4"}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-xl font-semibold">当前仓库读取</h2>
          <code className="rounded bg-white px-3 py-2 text-sm text-slate-700">{snapshot.apiBaseUrl}</code>
        </div>

        <div className="overflow-hidden rounded-md border border-line bg-white">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="border-b border-line bg-panel text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">文件</th>
                <th className="px-4 py-3 font-semibold">状态</th>
                <th className="px-4 py-3 font-semibold">来源</th>
                <th className="px-4 py-3 font-semibold">大小</th>
                <th className="px-4 py-3 font-semibold">更新时间</th>
              </tr>
            </thead>
            <tbody>
              {canonicalPaths.map((path) => {
                const file = filesByPath.get(path);
                const meta = file?.file;
                return (
                  <tr key={path} className="border-b border-line last:border-b-0">
                    <td className="max-w-[320px] px-4 py-3 font-medium">{path}</td>
                    <td className="px-4 py-3">{statusLabel(file?.status ?? "not_configured")}</td>
                    <td className="px-4 py-3 text-slate-600">{meta?.source ?? "-"}</td>
                    <td className="px-4 py-3 text-slate-600">{meta ? `${meta.size} B` : "-"}</td>
                    <td className="px-4 py-3 text-slate-600">{meta?.last_modified ?? "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
