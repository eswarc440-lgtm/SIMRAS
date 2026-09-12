import { useEffect, useMemo, useState } from "react";
import { Activity, Gauge, ShieldAlert, Sparkles } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, PageHeader } from "../../components/common/PageHeader";
import { StatCard } from "../../components/common/StatCard";
import { RiskBadge } from "../../components/common/StatusBadge";
import { AITabs } from "../../components/ai/AITabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { apiRequest } from "../../services/api";

const riskColors = ["var(--color-success)", "var(--color-warning)", "var(--color-danger)"];
const tooltipStyle = { background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 };

function Shell({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <DashboardLayout><div className="space-y-6"><PageHeader eyebrow="AI Intelligence" title={title} description={description} /><AITabs />{children}</div></DashboardLayout>;
}

type Overview = {
  total_assets: number;
  total_predictions?: number | null;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  average_health_score?: number | null;
  average_risk_score?: number | null;
  average_remaining_life?: number | null;
  risk_distribution?: Array<{ key: string; name: string; value: number }>;
  top_high_risk_assets?: Array<{ id: string; name?: string; asset_type?: string; district?: string; risk_score?: number | null; health_score?: number | null; confidence_score?: number | null }>;
};

type PredictionItem = {
  id: string | number;
  asset_id?: string;
  asset_name?: string;
  target?: string;
  value?: number | null;
  predicted_class?: string | null;
  confidence?: number | null;
  confidence_score?: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
  model_version?: string | null;
  feature_version?: string | null;
  status?: string | null;
  prediction_time?: string | null;
};

function riskFrom(score?: number | null): "low" | "medium" | "high" {
  return score != null && score >= 70 ? "high" : score != null && score >= 40 ? "medium" : "low";
}

function fmt(value?: number | null, digits = 1) {
  return value == null ? "N/A" : value.toFixed(digits);
}

export function AIOverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  useEffect(() => { apiRequest<Overview>("/api/v1/dashboard/overview").then(setOverview).catch(() => setOverview(null)); }, []);
  const riskDistribution = overview?.risk_distribution ?? [];
  const insights = overview?.top_high_risk_assets ?? [];

  return (
    <Shell title="AI Intelligence" description="Stored model outputs and governance-aware decision support. Unavailable values remain N/A or withheld.">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Average Health" value={overview?.average_health_score != null ? `${Math.round(overview.average_health_score)}%` : "N/A"} icon={Gauge} tone="accent" delta="Stored health outputs" />
        <StatCard label="Stored Predictions" value={overview?.total_predictions != null ? overview.total_predictions.toLocaleString() : "N/A"} icon={Sparkles} delta="Prediction table records" />
        <StatCard label="High Risk Assets" value={overview ? overview.high_risk_assets.toLocaleString() : "—"} icon={ShieldAlert} tone="danger" delta="Risk score ≥ 70" />
        <StatCard label="Average RUL" value={overview?.average_remaining_life != null ? `${overview.average_remaining_life.toFixed(1)} yrs` : "N/A"} icon={Activity} tone="success" delta="Only where stored" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Risk Distribution" subtitle="Current stored risk classifications">
          <div className="h-72">
            {riskDistribution.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2}>{riskDistribution.map((entry, index) => <Cell key={entry.key} fill={riskColors[index % riskColors.length]} stroke="var(--color-card)" strokeWidth={2} />)}</Pie><Legend wrapperStyle={{ fontSize: 12 }} /><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No stored risk classifications available.</div>}
          </div>
        </ChartCard>

        <ChartCard title="Highest Stored Risk" subtitle="Current database ranking">
          <ul className="divide-y">
            {insights.length === 0 ? <li className="py-4 text-sm text-muted-foreground">No stored risk predictions are available.</li> : insights.slice(0, 6).map((asset) => <li key={asset.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 py-3 first:pt-0"><div><p className="text-sm font-medium">{asset.name ?? asset.id}</p><p className="mt-1 text-xs text-muted-foreground">{asset.id} · {asset.district ?? "District N/A"}</p><p className="mt-1 font-mono text-[11px] text-muted-foreground">Confidence {asset.confidence_score != null ? `${Math.round(asset.confidence_score * 100)}%` : "N/A"}</p></div><div className="text-right"><RiskBadge risk={riskFrom(asset.risk_score)} /><p className="mt-2 text-sm font-semibold">{fmt(asset.risk_score)}</p></div></li>)}
          </ul>
        </ChartCard>
      </div>
    </Shell>
  );
}

export function PredictionsPage() {
  const [items, setItems] = useState<PredictionItem[]>([]);
  useEffect(() => {
    apiRequest<{ items?: PredictionItem[]; predictions?: PredictionItem[] }>("/api/v1/predictions?limit=100")
      .then((payload) => setItems(payload.items ?? payload.predictions ?? []))
      .catch(() => setItems([]));
  }, []);

  return (
    <Shell title="Predictions" description="Latest stored prediction records. No frontend confidence or prediction values are generated.">
      <ChartCard title="Prediction Records" subtitle={`${items.length} records returned by the live backend`}>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Asset</TableHead><TableHead>Target</TableHead><TableHead>Value</TableHead><TableHead>Class</TableHead><TableHead>Confidence</TableHead><TableHead>Status</TableHead><TableHead>Model</TableHead><TableHead>Time</TableHead></TableRow></TableHeader>
            <TableBody>
              {items.map((item) => {
                const confidence = item.confidence_score ?? item.confidence;
                return <TableRow key={String(item.id)}><TableCell><span className="font-mono text-xs">{item.asset_id ?? "N/A"}</span><span className="block text-sm">{item.asset_name ?? ""}</span></TableCell><TableCell>{item.target ?? "N/A"}</TableCell><TableCell className="tabular-nums">{fmt(item.value, 2)}</TableCell><TableCell>{item.predicted_class ?? "N/A"}</TableCell><TableCell>{confidence != null ? `${Math.round(confidence * 100)}%` : "N/A"}</TableCell><TableCell>{item.status ?? "N/A"}</TableCell><TableCell><span className="text-xs">{item.model_version ?? "N/A"}</span></TableCell><TableCell className="text-xs text-muted-foreground">{item.prediction_time ? new Date(item.prediction_time).toLocaleString() : "N/A"}</TableCell></TableRow>;
              })}
            </TableBody>
          </Table>
        </div>
      </ChartCard>
    </Shell>
  );
}

export function RiskAnalysisPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { apiRequest<any>("/api/v1/analytics/risk-analysis").then(setData).catch(() => setData(null)); }, []);
  const distribution = data?.risk_distribution ?? [];
  const districts = data?.district_risk ?? [];
  return (
    <Shell title="Risk Analysis" description="Risk distribution calculated from current stored risk predictions.">
      <div className="grid gap-4 sm:grid-cols-3">
        {(["high", "medium", "low"] as const).map((key) => {
          const value = distribution.find((item: any) => item.key === key)?.value ?? 0;
          return <StatCard key={key} label={`${key[0].toUpperCase()}${key.slice(1)} Risk`} value={value} tone={key === "high" ? "danger" : key === "medium" ? "warning" : "success"} icon={key === "high" ? ShieldAlert : key === "medium" ? Activity : Gauge} delta="Current stored classification" />;
        })}
      </div>
      <ChartCard title="District Risk Coverage" subtitle="Real asset and high-risk counts by district">
        <div className="h-80">{districts.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={districts.slice(0, 15)} margin={{ left: -12, right: 8, top: 8 }}><CartesianGrid stroke="var(--color-border)" vertical={false} /><XAxis dataKey="district" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} interval={0} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} /><Bar dataKey="assets" name="Assets" fill="var(--color-chart-1)" /><Bar dataKey="high_risk" name="High risk" fill="var(--color-danger)" /></BarChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No district risk data available.</div>}</div>
      </ChartCard>
    </Shell>
  );
}

function firstRegistry(payload: any): any {
  if (!payload) return null;
  if (payload.model_name || payload.stage) return payload;
  if (payload.model && typeof payload.model === "object") return payload.model;
  if (Array.isArray(payload.items) && payload.items.length) return payload.items[0];
  if (Array.isArray(payload.models) && payload.models.length) return payload.models[0];
  if (payload.registry && typeof payload.registry === "object") {
    if (Array.isArray(payload.registry.items) && payload.registry.items.length) return payload.registry.items[0];
    return payload.registry;
  }
  return payload;
}

export function ModelPerformancePage() {
  const [payload, setPayload] = useState<any>(null);
  useEffect(() => { apiRequest<any>("/api/v1/analytics/models/status").then(setPayload).catch(() => setPayload(null)); }, []);
  const model = firstRegistry(payload);
  const metrics = useMemo(() => {
    const source = model?.metrics && typeof model.metrics === "object" ? model.metrics : payload?.metrics && typeof payload.metrics === "object" ? payload.metrics : {};
    return Object.entries(source).filter(([, value]) => ["number", "string", "boolean"].includes(typeof value)).slice(0, 18);
  }, [model, payload]);

  return (
    <Shell title="Model Performance & Governance" description="Values are read from the live model registry/status endpoint; no hardcoded R², MAE or RMSE values are shown.">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Model" value={model?.model_name ?? "N/A"} icon={Sparkles} />
        <StatCard label="Version" value={model?.version ?? "N/A"} icon={Activity} />
        <StatCard label="Stage" value={model?.stage ? String(model.stage).replaceAll("_", " ") : "N/A"} icon={ShieldAlert} tone="warning" />
        <StatCard label="Feature Version" value={model?.feature_version ?? "N/A"} icon={Gauge} />
      </div>
      <ChartCard title="Registered Metrics" subtitle="Latest available model-registry metrics">
        {metrics.length === 0 ? <div className="p-4 text-sm text-muted-foreground">No flat metrics are available from the current model registry response.</div> : <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{metrics.map(([key, value]) => <div key={key} className="rounded-md border bg-surface p-4"><dt className="text-xs text-muted-foreground">{key.replaceAll("_", " ")}</dt><dd className="mt-2 break-words font-mono text-sm font-semibold">{String(value)}</dd></div>)}</dl>}
      </ChartCard>
      <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">Model outputs remain decision-support information. Governance stage is displayed exactly as returned by the backend.</div>
    </Shell>
  );
}
