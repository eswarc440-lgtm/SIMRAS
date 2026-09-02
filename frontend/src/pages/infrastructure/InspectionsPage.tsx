import { createElement } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Database,
  ExternalLink,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";

type RawItem = Record<string, unknown>;

interface AssetOption {
  asset_code: string;
  name: string;
}

interface InspectionItem {
  id: string;
  asset_code: string;
  asset_name: string | null;
  inspection_type: string | null;
  inspection_date: string | null;
  inspector: string | null;
  score: number | null;
  condition: string | null;
  notes: string | null;
  quality_flag: string | null;
  is_synthetic: boolean;
}

function backendRoot() {
  const configured =
    import.meta.env.VITE_BACKEND_URL ??
    import.meta.env.VITE_API_BASE_URL ??
    import.meta.env.VITE_API_BASE_URL;

  return String(configured)
    .replace(/\/api\/v1\/?$/i, "")
    .replace(/\/+$/, "");
}

const BACKEND = backendRoot();

function apiUrl(path: string) {
  return `${BACKEND}${path.startsWith("/") ? path : `/${path}`}`;
}

function asText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const result = String(value).trim();
  return result ? result : null;
}

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractItems(payload: unknown): RawItem[] {
  if (Array.isArray(payload)) {
    return payload.filter(
      (item): item is RawItem => Boolean(item && typeof item === "object"),
    );
  }

  if (!payload || typeof payload !== "object") return [];

  const object = payload as Record<string, unknown>;
  for (const key of ["items", "data", "results"]) {
    const value = object[key];
    if (Array.isArray(value)) {
      return value.filter(
        (item): item is RawItem => Boolean(item && typeof item === "object"),
      );
    }
  }

  return [];
}

function mapInspection(item: RawItem): InspectionItem {
  const inspector = asText(item.inspector ?? item.inspector_name);
  const notes = asText(item.notes ?? item.remarks ?? item.findings);
  const quality = asText(item.quality_flag);

  const explicitSynthetic =
    item.is_synthetic === true ||
    String(item.is_synthetic ?? "").toLowerCase() === "true";

  const legacySynthetic =
    (inspector ?? "").toLowerCase().includes("synthetic seed") ||
    (notes ?? "").toLowerCase().includes("replace with an approved inspection") ||
    (quality ?? "").toUpperCase().includes("DEMONSTRATION") ||
    (quality ?? "").toUpperCase().includes("SYNTHETIC");

  return {
    id: String(item.id ?? item.inspection_id ?? ""),
    asset_code:
      asText(item.asset_code ?? item.asset_id) ?? "UNKNOWN",
    asset_name: asText(item.asset_name ?? item.name),
    inspection_type: asText(item.inspection_type ?? item.type),
    inspection_date: asText(item.inspection_date ?? item.date),
    inspector,
    score: asNumber(
      item.inspection_score ?? item.condition_score ?? item.score,
    ),
    condition: asText(item.condition),
    notes,
    quality_flag: quality,
    is_synthetic: explicitSynthetic || legacySynthetic,
  };
}

async function getJson(path: string) {
  const response = await fetch(apiUrl(path), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = String(body?.detail ?? body?.message ?? message);
    } catch {
      // Keep HTTP message.
    }
    throw new Error(message);
  }

  return response.json();
}

function formatDate(value: string | null) {
  if (!value) return "N/A";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function scoreText(value: number | null) {
  return value === null ? "N/A" : `${value.toFixed(1)}/100`;
}

function conditionTone(condition: string | null) {
  const value = (condition ?? "").toUpperCase();

  if (["GOOD", "HEALTHY", "SOUND", "SATISFACTORY"].includes(value)) {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700";
  }
  if (["FAIR", "MONITOR", "NEEDS MONITORING"].includes(value)) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-700";
  }
  if (["POOR", "CRITICAL", "UNSAFE"].includes(value)) {
    return "border-red-500/30 bg-red-500/10 text-red-700";
  }

  return "border-border bg-muted/50 text-muted-foreground";
}

export function InspectionsPage() {
  const [rows, setRows] = useState<InspectionItem[]>([]);
  const [assets, setAssets] = useState<AssetOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [conditionFilter, setConditionFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");

  const [showForm, setShowForm] = useState(false);
  const [assetCode, setAssetCode] = useState("");
  const [inspectionDate, setInspectionDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [inspectionType, setInspectionType] = useState("ROUTINE");
  const [condition, setCondition] = useState("");
  const [score, setScore] = useState("");
  const [inspector, setInspector] = useState("");
  const [notes, setNotes] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);

    try {
      const [inspectionPayload, assetPayload] = await Promise.all([
        getJson("/api/v1/inspections?limit=1000"),
        getJson("/api/v1/assets?limit=1000"),
      ]);

      const inspectionRows = extractItems(inspectionPayload).map(mapInspection);
      const assetRows = extractItems(assetPayload)
        .map((item) => ({
          asset_code:
            asText(item.asset_code ?? item.asset_id ?? item.id) ?? "",
          name: asText(item.name) ?? "Unnamed asset",
        }))
        .filter((item) => item.asset_code);

      setRows(inspectionRows);
      setAssets(assetRows);
      setAssetCode((current) => current || assetRows[0]?.asset_code || "");
    } catch (reason) {
      setRows([]);
      setAssets([]);
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const syntheticCount = useMemo(
    () => rows.filter((row) => row.is_synthetic).length,
    [rows],
  );

  const realRows = useMemo(
    () => rows.filter((row) => !row.is_synthetic),
    [rows],
  );

  const conditionOptions = useMemo(
    () =>
      Array.from(
        new Set(
          realRows
            .map((row) => row.condition)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort(),
    [realRows],
  );

  const typeOptions = useMemo(
    () =>
      Array.from(
        new Set(
          realRows
            .map((row) => row.inspection_type)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort(),
    [realRows],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return realRows.filter((row) => {
      const matchesSearch =
        !q ||
        [
          row.asset_code,
          row.asset_name ?? "",
          row.inspection_type ?? "",
          row.inspector ?? "",
          row.condition ?? "",
          row.notes ?? "",
        ].some((value) => value.toLowerCase().includes(q));

      return (
        matchesSearch &&
        (conditionFilter === "ALL" || row.condition === conditionFilter) &&
        (typeFilter === "ALL" || row.inspection_type === typeFilter)
      );
    });
  }, [conditionFilter, query, realRows, typeFilter]);

  const inspectedAssets = useMemo(
    () => new Set(realRows.map((row) => row.asset_code)).size,
    [realRows],
  );

  const recentCount = useMemo(() => {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;

    return realRows.filter((row) => {
      if (!row.inspection_date) return false;
      const timestamp = new Date(row.inspection_date).getTime();
      return Number.isFinite(timestamp) && timestamp >= cutoff;
    }).length;
  }, [realRows]);

  async function saveInspection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveMessage(null);

    if (!assetCode) {
      setSaveMessage("Select an asset.");
      return;
    }

    if (!adminKey.trim()) {
      setSaveMessage("Administrator API key is required.");
      return;
    }

    const parsedScore = score.trim() === "" ? null : Number(score);
    if (
      parsedScore !== null &&
      (!Number.isFinite(parsedScore) || parsedScore < 0 || parsedScore > 100)
    ) {
      setSaveMessage("Score must be between 0 and 100.");
      return;
    }

    setSaving(true);

    try {
      const response = await fetch(apiUrl("/api/v1/inspections"), {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Admin-API-Key": adminKey,
        },
        body: JSON.stringify({
          asset_code: assetCode,
          inspection_date: inspectionDate,
          inspection_type: inspectionType || "ROUTINE",
          condition: condition.trim() || null,
          score: parsedScore,
          inspector: inspector.trim() || null,
          notes: notes.trim() || null,
        }),
      });

      if (!response.ok) {
        let message = `${response.status} ${response.statusText}`;
        try {
          const body = await response.json();
          message = String(body?.detail ?? body?.message ?? message);
        } catch {
          // Keep status.
        }
        throw new Error(message);
      }

      setSaveMessage("Approved inspection stored successfully.");
      setCondition("");
      setScore("");
      setInspector("");
      setNotes("");
      setAdminKey("");
      await load();
      setShowForm(false);
    } catch (reason) {
      setSaveMessage(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-5">
        <header className="flex flex-col gap-4 border-b pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.28em] text-muted-foreground">
              Infrastructure Operations
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              Inspections
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Approved inspection history from FastAPI and PostgreSQL.
              Synthetic demonstration records are excluded from this operational view.
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => void load()}
              disabled={loading}
            >
              <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>

            <Button type="button" onClick={() => setShowForm((value) => !value)}>
              {showForm ? <X className="size-4" /> : <Plus className="size-4" />}
              {showForm ? "Close" : "New Inspection"}
            </Button>
          </div>
        </header>

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Approved inspections", realRows.length, CheckCircle2],
            ["Assets inspected", inspectedAssets, Database],
            ["Last 30 days", recentCount, CalendarDays],
            ["Demo rows excluded", syntheticCount, ShieldCheck],
          ].map(([label, value, Icon]) => (
            <div key={String(label)} className="rounded-xl border bg-card p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider text-muted-foreground">
                  {String(label)}
                </span>
                {createElement(Icon as any, { className: "size-4 text-muted-foreground" })}
              </div>
              <strong className="mt-3 block text-2xl">
                {Number(value).toLocaleString()}
              </strong>
            </div>
          ))}
        </section>

        {showForm && (
          <section className="rounded-xl border bg-card p-5">
            <h2 className="font-semibold">Add approved inspection</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Writes use the protected backend POST endpoint. The API key is
              not hard-coded into the frontend.
            </p>

            <form
              onSubmit={saveInspection}
              className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4"
            >
              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Asset</span>
                <select
                  value={assetCode}
                  onChange={(event) => setAssetCode(event.target.value)}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                >
                  {assets.map((asset) => (
                    <option key={asset.asset_code} value={asset.asset_code}>
                      {asset.asset_code} Â· {asset.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Inspection date</span>
                <Input
                  type="date"
                  value={inspectionDate}
                  onChange={(event) => setInspectionDate(event.target.value)}
                  required
                />
              </label>

              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Inspection type</span>
                <Input
                  value={inspectionType}
                  onChange={(event) => setInspectionType(event.target.value)}
                  placeholder="ROUTINE"
                  required
                />
              </label>

              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Condition</span>
                <Input
                  value={condition}
                  onChange={(event) => setCondition(event.target.value)}
                  placeholder="GOOD / FAIR / POOR..."
                />
              </label>

              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Score (0-100)</span>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={score}
                  onChange={(event) => setScore(event.target.value)}
                  placeholder="N/A"
                />
              </label>

              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-muted-foreground">Inspector</span>
                <Input
                  value={inspector}
                  onChange={(event) => setInspector(event.target.value)}
                  placeholder="Approved inspector / agency"
                />
              </label>

              <label className="space-y-1.5 text-sm md:col-span-2">
                <span className="text-xs text-muted-foreground">
                  Administrator API key
                </span>
                <Input
                  type="password"
                  value={adminKey}
                  onChange={(event) => setAdminKey(event.target.value)}
                  placeholder="Required for approved write"
                  autoComplete="off"
                />
              </label>

              <label className="space-y-1.5 text-sm md:col-span-2 xl:col-span-4">
                <span className="text-xs text-muted-foreground">Findings / notes</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  className="min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="Observed defects, measurements, references, follow-up..."
                />
              </label>

              <div className="md:col-span-2 xl:col-span-4">
                <p className="mb-3 text-xs text-amber-700">
                  A generic inspection score is not automatically treated as an
                  NBI/FHWA engineering rating.
                </p>

                {saveMessage && <p className="mb-3 text-sm">{saveMessage}</p>}

                <Button type="submit" disabled={saving || assets.length === 0}>
                  {saving ? "Saving..." : "Save Approved Inspection"}
                </Button>
              </div>
            </form>
          </section>
        )}

        <section className="rounded-xl border bg-card p-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_220px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search asset, type, inspector, condition..."
                className="pl-9"
              />
            </div>

            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
              className="h-10 rounded-md border bg-background px-3 text-sm"
            >
              <option value="ALL">All inspection types</option>
              {typeOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>

            <select
              value={conditionFilter}
              onChange={(event) => setConditionFilter(event.target.value)}
              className="h-10 rounded-md border bg-background px-3 text-sm"
            >
              <option value="ALL">All conditions</option>
              {conditionOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="overflow-hidden rounded-xl border bg-card">
          <div className="flex items-center justify-between border-b px-5 py-4">
            <div>
              <h2 className="font-semibold">Approved inspection register</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {filtered.length} of {realRows.length} real records
              </p>
            </div>
            <span className="text-xs text-muted-foreground">PostgreSQL / FastAPI</span>
          </div>

          {loading ? (
            <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">
              Loading real inspection records...
            </div>
          ) : error ? (
            <div className="grid min-h-48 place-items-center p-8 text-center">
              <div>
                <strong className="text-destructive">Inspection API connection failed</strong>
                <p className="mt-2 text-sm text-muted-foreground">{error}</p>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="grid min-h-48 place-items-center p-8 text-center">
              <div className="max-w-lg">
                <ShieldCheck className="mx-auto size-7 text-muted-foreground" />
                <strong className="mt-3 block">No approved inspection records available</strong>
                <p className="mt-2 text-sm text-muted-foreground">
                  Demonstration/synthetic inspection rows are intentionally hidden.
                  Add an approved inspection or import an authoritative inspection dataset.
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y">
              {filtered.map((row) => (
                <article
                  key={`${row.id}-${row.asset_code}`}
                  className="grid gap-4 px-5 py-4 lg:grid-cols-[1.25fr_0.85fr_0.7fr_0.85fr_auto] lg:items-center"
                >
                  <div className="min-w-0">
                    <p className="font-mono text-xs text-muted-foreground">
                      {row.asset_code}
                    </p>
                    <h3 className="mt-1 truncate font-semibold">
                      {row.asset_name ?? row.asset_code}
                    </h3>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {row.notes ?? "No findings/notes recorded."}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">Inspection</p>
                    <p className="mt-1 text-sm">{row.inspection_type ?? "N/A"}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(row.inspection_date)}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">Condition</p>
                    <span
                      className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${conditionTone(
                        row.condition,
                      )}`}
                    >
                      {row.condition ?? "N/A"}
                    </span>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">Score / inspector</p>
                    <p className="mt-1 text-sm font-medium">{scoreText(row.score)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {row.inspector ?? "Inspector N/A"}
                    </p>
                    <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                      {row.quality_flag ?? "Quality N/A"}
                    </p>
                  </div>

                  <a
                    href={`/digital-twin?asset=${encodeURIComponent(row.asset_code)}`}
                    className="inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium hover:bg-muted"
                  >
                    Twin
                    <ExternalLink className="size-3.5" />
                  </a>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </DashboardLayout>
  );
}

