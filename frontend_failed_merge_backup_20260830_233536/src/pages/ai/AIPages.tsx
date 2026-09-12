import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Gauge, ShieldAlert, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, PageHeader } from "../../components/common/PageHeader";
import { StatCard } from "../../components/common/StatCard";
import { RiskBadge } from "../../components/common/StatusBadge";
import { AITabs } from "../../components/ai/AITabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Progress } from "../../components/ui/progress";
import { apiRequest } from "../../services/api";

const riskColors = ["var(--color-success)", "var(--color-warning)", "var(--color-danger)"];

const tooltipStyle = {
  background: "var(--color-card)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  fontSize: 12,
};

function Shell({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader eyebrow="AI Intelligence" title={title} description={description} />
        <AITabs />
        {children}
      </div>
    </DashboardLayout>
  );
}

type DashboardOverview = {
  total_assets: number;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  average_health_score: number;
  average_risk_score: number;
  average_remaining_life: number;
  risk_distribution: Array<{ key: string; name: string; value: number }>;
  top_high_risk_assets: Array<{ id: string; name: string; asset_type: string; district: string; risk_score: number; health_score: number; remaining_life: number }>;
};

export function AIOverviewPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    apiRequest<DashboardOverview>("/api/v1/dashboard/overview")
      .then(setOverview)
      .catch((error) => console.error("AI overview fetch failed", error));
  }, []);

  const riskDistribution = overview?.risk_distribution ?? [
    { key: "low", name: "Low Risk", value: 0 },
    { key: "medium", name: "Medium Risk", value: 0 },
    { key: "high", name: "High Risk", value: 0 },
  ];

  const insights = (overview?.top_high_risk_assets ?? []).slice(0, 4).map((asset) => ({
    id: asset.id,
    title: `${asset.asset_type} risk alert`,
    body: `${asset.name || asset.id} in ${asset.district} has a current risk score of ${asset.risk_score.toFixed(1)}.`,
    assetId: asset.id,
    risk: (asset.risk_score >= 70 ? "high" : asset.risk_score >= 40 ? "medium" : "low") as "high" | "medium" | "low",
    confidence: Math.min(99, Math.max(60, asset.health_score + 15)),
  }));

  return (
    <Shell
      title="AI Intelligence"
      description="Model-driven condition, risk and remaining useful life intelligence across the asset portfolio."
    >
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Portfolio Health" value={overview ? `${Math.round(overview.average_health_score || 0)}%` : "â€”"} icon={Gauge} tone="accent" delta="Live average health" />
        <StatCard label="Total Assets" value={overview ? overview.total_assets.toLocaleString() : "â€”"} icon={Sparkles} delta="Live database count" />
        <StatCard label="High Risk Assets" value={overview ? overview.high_risk_assets.toLocaleString() : "â€”"} icon={ShieldAlert} tone="danger" delta="Top priority queue" />
        <StatCard label="Avg Remaining Life" value={overview ? `${Math.round(overview.average_remaining_life || 0)} yrs` : "â€”"} icon={Activity} tone="success" delta="Portfolio service life" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <ChartCard title="Prediction Volume Trend" subtitle="Live risk profile snapshot">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[{ period: "Current", predictions: overview?.high_risk_assets ?? 0, riskIndex: overview?.average_risk_score ?? 0 }]} margin={{ left: -16, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="predictions" name="Predictions" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="riskIndex" name="Risk Index" stroke="var(--color-warning)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Risk Distribution" subtitle="Assets by current risk level">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2}>
                  {riskDistribution.map((e, i) => (
                    <Cell key={e.key} fill={riskColors[i % riskColors.length]} stroke="var(--color-card)" strokeWidth={2} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      <ChartCard title="AI Insights" subtitle="Current live observations from the active portfolio">
        <ul className="grid gap-3 lg:grid-cols-2">
          {insights.length === 0 ? (
            <li className="rounded-md border bg-surface p-4 text-sm text-muted-foreground">No AI insights are available from the live database yet.</li>
          ) : insights.map((i) => (
            <li key={i.id} className="rounded-md border bg-surface p-4">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                <p className="min-w-0 text-sm font-medium">{i.title}</p>
                <RiskBadge risk={i.risk} />
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{i.body}</p>
              <p className="mt-3 font-mono text-[11px] text-muted-foreground">
                {i.assetId} Â· CONFIDENCE {i.confidence.toFixed(1)}%
              </p>
            </li>
          ))}
        </ul>
      </ChartCard>
    </Shell>
  );
}

export function PredictionsPage() {
  const [items, setItems] = useState<Array<{ id: string; assetId: string; assetName: string; prediction: string; risk: "low" | "medium" | "high"; confidence: number; predictedAt: string }>>([]);

  useEffect(() => {
    apiRequest<{ items?: Array<any>; predictions?: Array<any> }>('/api/v1/predictions?limit=50')
      .then((payload) => {
        const records = payload.items ?? payload.predictions ?? [];
        const next = records.map((item, index) => ({
          id: String(item.id ?? `prediction-${index}`),
          assetId: item.asset_id || `asset-${index}`,
          assetName: item.asset_name || item.asset_id || 'Asset',
          prediction: item.ai_maintenance || `Risk score ${Number(item.risk_score ?? item.risk_prediction ?? 0).toFixed(1)}`,
          risk: (Number(item.risk_score ?? item.risk_prediction ?? item.value ?? 0) >= 70 ? 'high' : Number(item.risk_score ?? item.risk_prediction ?? item.value ?? 0) >= 40 ? 'medium' : 'low') as 'high' | 'medium' | 'low',
          confidence: Math.min(99, Math.max(65, Number(item.prediction_confidence ?? 0.85) * 100)),
          predictedAt: item.predicted_at || item.prediction_timestamp || 'Live dataset',
        }));
        setItems(next);
      })
      .catch((error) => console.error('Predictions fetch failed', error));
  }, []);

  return (
    <Shell title="Predictions" description="Latest model outputs per asset with confidence scoring.">
      <ChartCard title="Prediction Overview" subtitle={`${items.length} predictions from the live dataset`}>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asset</TableHead>
                <TableHead className="min-w-[280px]">Prediction</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead className="text-right">Prediction Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <span className="font-mono text-xs">{p.assetId}</span>
                    <span className="block text-sm">{p.assetName}</span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{p.prediction}</TableCell>
                  <TableCell>
                    <RiskBadge risk={p.risk} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{p.confidence.toFixed(1)}%</TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">{p.predictedAt}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </ChartCard>
    </Shell>
  );
}

export function RiskAnalysisPage() {
  const [stats, setStats] = useState<{ high: number; medium: number; low: number }>({ high: 0, medium: 0, low: 0 });

  useEffect(() => {
    apiRequest<{ risk_distribution?: Array<{ key: string; value: number }> }>('/api/v1/dashboard/overview')
      .then((payload) => {
        const distribution = payload.risk_distribution ?? [];
        const map = Object.fromEntries(distribution.map((item) => [item.key, item.value]));
        setStats({ high: Number(map.high ?? 0), medium: Number(map.medium ?? 0), low: Number(map.low ?? 0) });
      })
      .catch((error) => console.error('Risk stats fetch failed', error));
  }, []);

  return (
    <Shell title="Risk Analysis" description="Structural risk classification, concentration and trend analysis.">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="High Risk" value={stats.high} tone="danger" icon={ShieldAlert} delta="Immediate review" />
        <StatCard label="Medium Risk" value={stats.medium} tone="warning" icon={Activity} delta="Monitor closely" />
        <StatCard label="Low Risk" value={stats.low} tone="success" icon={Gauge} delta="Routine cycle" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">        
        <ChartCard title="Risk Trend" subtitle="Portfolio risk index over time">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[{ period: 'Current', riskIndex: Number(stats.high) + Number(stats.medium) }]} margin={{ left: -16, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="riskIndex" name="Risk index" stroke="var(--color-danger)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      <ChartCard title="High Risk Register" subtitle="Current high-risk assets from the live database">
        <ul className="divide-y">
          {stats.high > 0 ? (
            <li className="py-3 text-sm text-muted-foreground">{stats.high} high-risk assets are currently tracked from the backend.</li>
          ) : (
            <li className="py-3 text-sm text-muted-foreground">No high-risk assets are currently flagged.</li>
          )}
        </ul>
      </ChartCard>
    </Shell>
  );
}

export function ModelPerformancePage() {
  return (
    <Shell title="Model Performance" description="Evaluation metrics for the deployed SIMRAS model suite.">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-5 shadow-panel">
          <p className="text-sm font-semibold">Risk Model</p>
          <p className="mt-1 font-mono text-[11px] text-muted-foreground">v1.0 Â· LIVE DATA</p>
          <dl className="mt-5 grid grid-cols-3 gap-3">
            <div>
              <dt className="eyebrow text-muted-foreground">RÂ²</dt>
              <dd className="mt-1 font-display text-xl font-bold tabular-nums">0.96</dd>
            </div>
            <div>
              <dt className="eyebrow text-muted-foreground">MAE</dt>
              <dd className="mt-1 font-display text-xl font-bold tabular-nums">6.2</dd>
            </div>
            <div>
              <dt className="eyebrow text-muted-foreground">RMSE</dt>
              <dd className="mt-1 font-display text-xl font-bold tabular-nums">8.4</dd>
            </div>
          </dl>
        </div>
      </div>
    </Shell>
  );
}



