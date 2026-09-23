import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  Database,
  Download,
  RefreshCw,
  Search,
} from "lucide-react";

import { DashboardLayout } from "../../layouts/DashboardLayout";
import {
  ChartCard,
  EmptyState,
  PageHeader,
} from "../../components/common/PageHeader";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { API_BASE_URL } from "../../services/api";

type RawRecord = Record<string, unknown>;

interface RealAsset {
  id: string;
  name: string;
  assetType: string;
  district: string | null;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  builtYear: number | null;
  designLife: number | null;
  age: number | null;
  condition: string | null;
  owner: string | null;
  material: string | null;
  identityStatus: string | null;
  status: string | null;
  healthScore: number | null;
  riskScore: number | null;
  riskLevel: string | null;
  remainingLife: number | null;
  predictionTime: string | null;
  confidence: number | null;
}

interface InspectionRow {
  id: string;
  date: string | null;
  inspector: string | null;
  condition: string | null;
  score: number | null;
  notes: string | null;
}

function asText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text ? text : null;
}

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractItems(payload: unknown): RawRecord[] {
  if (Array.isArray(payload)) {
    return payload.filter((item): item is RawRecord => Boolean(item && typeof item === "object"));
  }

  if (!payload || typeof payload !== "object") return [];

  const object = payload as Record<string, unknown>;

  for (const key of ["items", "assets", "data", "results"]) {
    const value = object[key];
    if (Array.isArray(value)) {
      return value.filter((item): item is RawRecord => Boolean(item && typeof item === "object"));
    }
  }

  if (object.type === "FeatureCollection" && Array.isArray(object.features)) {
    return object.features
      .filter((feature): feature is RawRecord => Boolean(feature && typeof feature === "object"))
      .map((feature) => {
        const properties =
          feature.properties && typeof feature.properties === "object"
            ? (feature.properties as RawRecord)
            : {};
        const geometry =
          feature.geometry && typeof feature.geometry === "object"
            ? (feature.geometry as RawRecord)
            : {};
        const coordinates = Array.isArray(geometry.coordinates)
          ? geometry.coordinates
          : [];

        return {
          ...properties,
          longitude: properties.longitude ?? coordinates[0],
          latitude: properties.latitude ?? coordinates[1],
        };
      });
  }

  return [];
}

function mapAsset(asset: RawRecord): RealAsset {
  const id =
    asText(
      asset.asset_code ??
        asset.asset_id ??
        asset.canonical_code ??
        asset.code ??
        asset.id,
    ) ?? "UNKNOWN";

  return {
    id,
    name: asText(asset.name ?? asset.asset_name) ?? "Unnamed asset",
    assetType: asText(asset.asset_type ?? asset.type ?? asset.feature_type) ?? "other",
    district: asText(asset.district),
    location: asText(asset.location ?? asset.place ?? asset.district),
    latitude: asNumber(asset.latitude ?? asset.lat),
    longitude: asNumber(asset.longitude ?? asset.lng ?? asset.lon),
    builtYear: asNumber(asset.built_year),
    designLife: asNumber(asset.design_life ?? asset.design_life_years),
    age: asNumber(asset.age ?? asset.current_age),
    condition: asText(asset.condition),
    owner: asText(asset.owner),
    material: asText(asset.material),
    identityStatus: asText(asset.identity_status),
    status: asText(asset.status),
    healthScore: asNumber(asset.health_score),
    riskScore: asNumber(asset.risk_score),
    riskLevel: asText(asset.risk_level ?? asset.predicted_class),
    remainingLife: asNumber(
      asset.remaining_useful_life ??
        asset.remaining_life ??
        asset.remaining_life_years ??
        asset.rul_years,
    ),
    predictionTime: asText(asset.prediction_time ?? asset.predicted_at),
    confidence: asNumber(asset.confidence_score ?? asset.prediction_confidence),
  };
}

async function requestJson(path: string): Promise<unknown> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = String(body?.detail ?? body?.message ?? message);
    } catch {
      // Keep HTTP status message.
    }
    throw new Error(message);
  }

  return response.json();
}

async function loadRealAssets(): Promise<{
  items: RealAsset[];
  source: string;
}> {
  const candidates = [
    ["/api/v1/assets?limit=1000", "Asset registry / PostGIS"],
    ["/api/v1/infrastructure?limit=1000", "Infrastructure compatibility API"],
    ["/api/v1/assets/geojson", "Asset GeoJSON"],
    ["/api/v1/map/features?limit=1000", "Map features API"],
  ] as const;

  const failures: string[] = [];

  for (const [path, source] of candidates) {
    try {
      const payload = await requestJson(path);
      const records = extractItems(payload);
      const mapped = records
        .map(mapAsset)
        .filter((asset) => asset.id !== "UNKNOWN");

      if (mapped.length > 0) {
        const deduped = Array.from(
          new Map(mapped.map((asset) => [asset.id, asset])).values(),
        );
        return { items: deduped, source };
      }

      failures.push(`${source}: returned 0 rows`);
    } catch (error) {
      failures.push(
        `${source}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  throw new Error(failures.join(" | "));
}

async function loadRealAsset(id: string): Promise<RealAsset> {
  const candidates = [
    `/api/v1/infrastructure/${encodeURIComponent(id)}`,
    `/api/v1/assets/${encodeURIComponent(id)}`,
  ];

  for (const path of candidates) {
    try {
      const payload = await requestJson(path);
      if (payload && typeof payload === "object") {
        const object = payload as Record<string, unknown>;

        if (object.asset && typeof object.asset === "object") {
          return mapAsset(object.asset as RawRecord);
        }

        return mapAsset(object as RawRecord);
      }
    } catch {
      // Try next real backend endpoint.
    }
  }

  const registry = await loadRealAssets();
  const match = registry.items.find((asset) => asset.id === id);
  if (!match) throw new Error(`Asset ${id} not found in live backend`);
  return match;
}

async function loadInspections(id: string): Promise<InspectionRow[]> {
  const candidates = [
    `/api/v1/assets/${encodeURIComponent(id)}/inspections`,
    `/api/v1/inspections?asset_code=${encodeURIComponent(id)}&limit=100`,
  ];

  for (const path of candidates) {
    try {
      const payload = await requestJson(path);
      const records = extractItems(payload);
      if (records.length === 0 && Array.isArray(payload)) {
        return [];
      }

      return records.map((item, index) => ({
        id: asText(item.id ?? item.inspection_id) ?? `INS-${index + 1}`,
        date: asText(item.inspection_date ?? item.date),
        inspector: asText(item.inspector),
        condition: asText(item.condition),
        score: asNumber(item.score ?? item.inspection_score ?? item.condition_score),
        notes: asText(item.notes ?? item.finding ?? item.inspection_type),
      }));
    } catch {
      // Try next live endpoint.
    }
  }

  return [];
}

function healthBand(score: number | null) {
  if (score === null) return "N/A";
  if (score >= 80) return "Healthy";
  if (score >= 50) return "Warning";
  return "Critical";
}

function riskBand(asset: RealAsset) {
  if (asset.riskLevel) {
    const level = asset.riskLevel.toLowerCase();
    if (level.includes("high") || level.includes("critical")) return "High";
    if (level.includes("medium") || level.includes("moderate")) return "Medium";
    if (level.includes("low")) return "Low";
  }

  if (asset.riskScore === null) return "N/A";
  if (asset.riskScore >= 70) return "High";
  if (asset.riskScore >= 40) return "Medium";
  return "Low";
}

function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "good" | "warn" | "danger" | "neutral";
}) {
  const classes = {
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-700",
    danger: "border-red-500/30 bg-red-500/10 text-red-700",
    neutral: "border-border bg-muted/50 text-muted-foreground",
  };

  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${classes[tone]}`}
    >
      {children}
    </span>
  );
}

function scoreTone(value: string) {
  if (value === "Healthy" || value === "Low") return "good" as const;
  if (value === "Warning" || value === "Medium") return "warn" as const;
  if (value === "Critical" || value === "High") return "danger" as const;
  return "neutral" as const;
}

function fmt(value: string | number | null, suffix = "") {
  if (value === null || value === undefined || value === "") return "N/A";
  return `${value}${suffix}`;
}

function exportCsv(rows: RealAsset[]) {
  const headers = [
    "asset_code",
    "name",
    "asset_type",
    "district",
    "latitude",
    "longitude",
    "condition",
    "health_score",
    "risk_score",
    "risk_level",
    "identity_status",
    "owner",
    "material",
  ];

  const escape = (value: unknown) =>
    `"${String(value ?? "").replaceAll('"', '""')}"`;

  const csv = [
    headers.join(","),
    ...rows.map((asset) =>
      [
        asset.id,
        asset.name,
        asset.assetType,
        asset.district,
        asset.latitude,
        asset.longitude,
        asset.condition,
        asset.healthScore,
        asset.riskScore,
        asset.riskLevel,
        asset.identityStatus,
        asset.owner,
        asset.material,
      ]
        .map(escape)
        .join(","),
    ),
  ].join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = "simras-real-infrastructure-assets.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export function InfrastructurePage() {
  const [rows, setRows] = useState<RealAsset[]>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All types");
  const [health, setHealth] = useState("All health");
  const [risk, setRisk] = useState("All risk");
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("Backend");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await loadRealAssets();
      setRows(result.items);
      setSource(result.source);
    } catch (reason) {
      setRows([]);
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const types = useMemo(
    () =>
      Array.from(new Set(rows.map((asset) => asset.assetType)))
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b)),
    [rows],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return rows.filter((asset) => {
      const assetHealth = healthBand(asset.healthScore);
      const assetRisk = riskBand(asset);

      const searchMatch =
        !q ||
        [
          asset.id,
          asset.name,
          asset.assetType,
          asset.district ?? "",
          asset.location ?? "",
        ].some((value) => value.toLowerCase().includes(q));

      return (
        searchMatch &&
        (type === "All types" || asset.assetType === type) &&
        (health === "All health" || assetHealth === health) &&
        (risk === "All risk" || assetRisk === risk)
      );
    });
  }, [health, query, risk, rows, type]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Digital Infrastructure"
          title="Infrastructure Assets"
          description="Live infrastructure register from the SIMRAS FastAPI and PostgreSQL/PostGIS data layer."
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
                <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>

              <Button
                variant="outline"
                onClick={() => exportCsv(filtered)}
                disabled={filtered.length === 0}
              >
                <Download className="size-4" />
                Export
              </Button>
            </div>
          }
        />

        <section className="flex flex-wrap items-center gap-4 rounded-lg border bg-card px-4 py-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Database className="size-3.5" />
            Source: <strong className="text-foreground">{source}</strong>
          </span>
          <span>
            <strong className="text-foreground">{rows.length.toLocaleString()}</strong>{" "}
            live assets loaded
          </span>
          <span>{types.length} real asset types</span>
          {error && <span className="text-destructive">{error}</span>}
        </section>

        <section
          aria-label="Filters"
          className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <div className="min-w-0 space-y-1.5">
            <Label htmlFor="asset-search" className="text-xs text-muted-foreground">
              Search
            </Label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id="asset-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Asset ID, name, district or type"
                className="pl-9"
              />
            </div>
          </div>

          <div className="min-w-0 space-y-1.5">
            <Label className="text-xs text-muted-foreground">Asset Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All types">All types</SelectItem>
                {types.map((assetType) => (
                  <SelectItem key={assetType} value={assetType}>
                    {assetType}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="min-w-0 space-y-1.5">
            <Label className="text-xs text-muted-foreground">Health</Label>
            <Select value={health} onValueChange={setHealth}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["All health", "Healthy", "Warning", "Critical", "N/A"].map(
                  (value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="min-w-0 space-y-1.5">
            <Label className="text-xs text-muted-foreground">Risk</Label>
            <Select value={risk} onValueChange={setRisk}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["All risk", "Low", "Medium", "High", "N/A"].map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </section>

        <ChartCard
          title="Asset Register"
          subtitle={`${filtered.length.toLocaleString()} of ${rows.length.toLocaleString()} live assets`}
        >
          {loading ? (
            <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
              Loading real infrastructure records from FastAPI/PostGIS...
            </div>
          ) : error ? (
            <EmptyState
              title="Live data connection failed"
              description={error}
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="No assets match these filters"
              description="The live registry is connected. Adjust the search or filter criteria."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset ID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Real Type</TableHead>
                    <TableHead>District</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Identity</TableHead>
                    <TableHead>Condition</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {filtered.map((asset) => {
                    const healthValue = healthBand(asset.healthScore);
                    const riskValue = riskBand(asset);

                    return (
                      <TableRow key={asset.id}>
                        <TableCell>
                          <Link
                            to="/infrastructure/$id"
                            params={{ id: asset.id }}
                            className="font-mono text-xs text-primary underline underline-offset-4"
                          >
                            {asset.id}
                          </Link>
                        </TableCell>

                        <TableCell className="font-medium">{asset.name}</TableCell>
                        <TableCell className="capitalize text-muted-foreground">
                          {asset.assetType}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {asset.district ?? asset.location ?? "N/A"}
                        </TableCell>
                        <TableCell>
                          <Pill tone={scoreTone(healthValue)}>
                            {asset.healthScore !== null
                              ? `${asset.healthScore.toFixed(1)} · ${healthValue}`
                              : "N/A"}
                          </Pill>
                        </TableCell>
                        <TableCell>
                          <Pill tone={scoreTone(riskValue)}>
                            {asset.riskScore !== null
                              ? `${asset.riskScore.toFixed(1)} · ${riskValue}`
                              : riskValue}
                          </Pill>
                        </TableCell>
                        <TableCell>
                          <Pill
                            tone={
                              asset.identityStatus === "VERIFIED"
                                ? "good"
                                : "neutral"
                            }
                          >
                            {asset.identityStatus ?? "N/A"}
                          </Pill>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {asset.condition ?? "N/A"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </ChartCard>
      </div>
    </DashboardLayout>
  );
}

export function AssetDetailsPage({ id }: { id: string }) {
  const [asset, setAsset] = useState<RealAsset | null>(null);
  const [history, setHistory] = useState<InspectionRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    Promise.all([loadRealAsset(id), loadInspections(id)])
      .then(([assetResult, inspectionResult]) => {
        if (!active) return;
        setAsset(assetResult);
        setHistory(inspectionResult);
      })
      .catch((reason) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : String(reason));
      });

    return () => {
      active = false;
    };
  }, [id]);

  if (error) {
    return (
      <DashboardLayout>
        <EmptyState title="Unable to load live asset" description={error} />
      </DashboardLayout>
    );
  }

  if (!asset) {
    return (
      <DashboardLayout>
        <div className="grid min-h-64 place-items-center text-sm text-muted-foreground">
          Loading live asset...
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link
          to="/infrastructure"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to infrastructure
        </Link>

        <PageHeader
          eyebrow={`${asset.id} · ${asset.assetType}`}
          title={asset.name}
          description={`${asset.district ?? asset.location ?? "Location N/A"} · Live database record`}
          actions={
            <Button asChild>
              <a href={`/digital-twin?asset=${encodeURIComponent(asset.id)}`}>
                Open Digital Twin
              </a>
            </Button>
          }
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["Health score", fmt(asset.healthScore)],
            ["Risk score", fmt(asset.riskScore)],
            ["Remaining life", fmt(asset.remainingLife, asset.remainingLife !== null ? " years" : "")],
            ["Identity", asset.identityStatus ?? "N/A"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border bg-card p-4">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                {label}
              </p>
              <p className="mt-2 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="Live Asset Record" subtitle="PostgreSQL/PostGIS-backed attributes">
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {[
                ["Asset ID", asset.id],
                ["Type", asset.assetType],
                ["District", asset.district ?? "N/A"],
                ["Condition", asset.condition ?? "N/A"],
                ["Owner", asset.owner ?? "N/A"],
                ["Material", asset.material ?? "N/A"],
                ["Built year", fmt(asset.builtYear)],
                ["Design life", fmt(asset.designLife, asset.designLife !== null ? " years" : "")],
                ["Age", fmt(asset.age, asset.age !== null ? " years" : "")],
                [
                  "Coordinates",
                  asset.latitude !== null && asset.longitude !== null
                    ? `${asset.latitude.toFixed(6)}, ${asset.longitude.toFixed(6)}`
                    : "N/A",
                ],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="mt-1">{value}</dd>
                </div>
              ))}
            </dl>
          </ChartCard>

          <ChartCard title="Prediction State" subtitle="Stored SIMRAS outputs only">
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {[
                ["Health", fmt(asset.healthScore)],
                ["Risk", fmt(asset.riskScore)],
                ["Risk level", riskBand(asset)],
                ["RUL", fmt(asset.remainingLife, asset.remainingLife !== null ? " years" : "")],
                [
                  "Confidence",
                  asset.confidence !== null
                    ? `${Math.round(
                        asset.confidence <= 1
                          ? asset.confidence * 100
                          : asset.confidence,
                      )}%`
                    : "N/A",
                ],
                ["Prediction time", asset.predictionTime ?? "N/A"],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="mt-1">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 text-xs text-muted-foreground">
              Missing predictions are displayed as N/A rather than fabricated values.
            </p>
          </ChartCard>
        </div>

        <ChartCard
          title="Inspection History"
          subtitle={`${history.length} live records`}
          action={
            <Button asChild variant="outline" size="sm">
              <Link to="/infrastructure/$id/history" params={{ id }}>
                Full history
              </Link>
            </Button>
          }
        >
          {history.length === 0 ? (
            <EmptyState
              title="No linked inspection records"
              description="No inspection row is currently stored for this asset."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Condition</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Inspector / notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.slice(0, 5).map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-mono text-xs">{row.id}</TableCell>
                      <TableCell>{row.date ?? "N/A"}</TableCell>
                      <TableCell>{row.condition ?? "N/A"}</TableCell>
                      <TableCell>{fmt(row.score)}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {[row.inspector, row.notes].filter(Boolean).join(" · ") || "N/A"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </ChartCard>
      </div>
    </DashboardLayout>
  );
}

export function AssetHistoryPage({ id }: { id: string }) {
  const [asset, setAsset] = useState<RealAsset | null>(null);
  const [history, setHistory] = useState<InspectionRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    Promise.all([loadRealAsset(id), loadInspections(id)])
      .then(([assetResult, inspectionResult]) => {
        if (!active) return;
        setAsset(assetResult);
        setHistory(inspectionResult);
      })
      .catch((reason) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link
          to="/infrastructure/$id"
          params={{ id }}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to asset
        </Link>

        <PageHeader
          eyebrow={id}
          title="Inspection History"
          description={asset?.name ?? "Live inspection records"}
        />

        {error ? (
          <EmptyState title="Unable to load inspection records" description={error} />
        ) : (
          <ChartCard title="All inspections" subtitle={`${history.length} live records`}>
            {history.length === 0 ? (
              <EmptyState
                title="No inspection records"
                description="No inspection row is currently linked to this asset."
              />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Condition</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Inspector</TableHead>
                      <TableHead>Notes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="font-mono text-xs">{row.id}</TableCell>
                        <TableCell>{row.date ?? "N/A"}</TableCell>
                        <TableCell>{row.condition ?? "N/A"}</TableCell>
                        <TableCell>{fmt(row.score)}</TableCell>
                        <TableCell>{row.inspector ?? "N/A"}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {row.notes ?? "N/A"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </ChartCard>
        )}
      </div>
    </DashboardLayout>
  );
}
