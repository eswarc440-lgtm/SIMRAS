import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, BarChart3, Box, Building2, FileText, Map, ShieldAlert, Sparkles } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, PageHeader } from "../../components/common/PageHeader";
import { StatCard } from "../../components/common/StatCard";
import { RiskBadge } from "../../components/common/StatusBadge";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../hooks/useAuth";
import { apiRequest } from "../../services/api";

type Overview = {
  total_assets: number;
  total_predictions?: number | null;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  average_health_score?: number | null;
  average_risk_score?: number | null;
  district_distribution?: Array<{ district: string; count: number }>;
  asset_type_distribution?: Array<{ asset_type: string; count: number }>;
  risk_distribution?: Array<{ key: string; name: string; value: number }>;
  top_high_risk_assets?: Array<{
    id: string;
    name?: string;
    asset_type?: string;
    district?: string;
    risk_score?: number | null;
    health_score?: number | null;
    confidence_score?: number | null;
  }>;
  recent_assessments?: Array<{
    assessment_id: string;
    assessment_name: string;
    asset_id: string;
    risk_level?: string | null;
    health_score?: number | null;
    last_assessed?: string | null;
  }>;
};

const riskColors = ["var(--color-success)", "var(--color-warning)", "var(--color-danger)"];

const quickActions = [
  { to: "/infrastructure", label: "Asset Registry", icon: Building2 },
  { to: "/gis", label: "GIS", icon: Map },
  { to: "/digital-twin", label: "Digital Twin", icon: Box },
  { to: "/ai", label: "AI Intelligence", icon: Sparkles },
  { to: "/reports", label: "Reports", icon: FileText },
] as const;

function pct(value?: number | null) {
  return value == null ? "N/A" : `${Math.round(value)}%`;
}

export function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Overview>("/api/v1/dashboard/overview")
      .then(setOverview)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, []);

  const districts = useMemo(() => (overview?.district_distribution ?? []).slice(0, 10), [overview]);
  const types = useMemo(() => (overview?.asset_type_distribution ?? []).slice(0, 10), [overview]);
  const risks = overview?.risk_distribution ?? [];
  const highRisk = overview?.top_high_risk_assets ?? [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow={`Welcome${user?.name ? `, ${user.name}` : ""}`}
          title="Infrastructure Overview"
          description="Live portfolio data from FastAPI and PostgreSQL/PostGIS. Missing values remain unavailable instead of being fabricated."
          actions={<Button asChild><Link to="/reports">Generate Report<ArrowRight className="size-4" /></Link></Button>}
        />

        {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Assets" value={overview ? overview.total_assets.toLocaleString() : "â€”"} icon={Building2} delta="Current registry" />
          <StatCard label="Average Health" value={overview ? pct(overview.average_health_score) : "â€”"} icon={BarChart3} tone="success" delta="Stored health predictions only" />
          <StatCard label="High Risk" value={overview ? overview.high_risk_assets.toLocaleString() : "â€”"} icon={ShieldAlert} tone="danger" delta="Stored risk score â‰¥ 70" />
          <StatCard label="Stored Predictions" value={overview?.total_predictions != null ? overview.total_predictions.toLocaleString() : "N/A"} icon={Sparkles} tone="accent" delta="Prediction table records" />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="Risk Distribution" subtitle="Current stored risk classifications">
            <div className="h-72">
              {risks.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={risks} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2}>
                      {risks.map((entry, index) => <Cell key={entry.key} fill={riskColors[index % riskColors.length]} stroke="var(--color-card)" strokeWidth={2} />)}
                    </Pie>
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <div className="grid h-full place-items-center text-sm text-muted-foreground">No stored risk classifications available.</div>}
            </div>
          </ChartCard>

          <ChartCard title="Assets by Type" subtitle="Current registry distribution">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={types} margin={{ left: -12, right: 8, top: 8 }}>
                  <CartesianGrid stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="asset_type" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" name="Assets" fill="var(--color-chart-1)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard title="District Coverage" subtitle="Top districts by registered asset count">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={districts} margin={{ left: -12, right: 8, top: 8 }}>
                  <CartesianGrid stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="district" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" name="Assets" fill="var(--color-chart-2)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard title="Highest Stored Risk" subtitle="Current database ranking">
            <ul className="divide-y">
              {highRisk.length === 0 ? (
                <li className="py-4 text-sm text-muted-foreground">No assets currently have a stored risk prediction.</li>
              ) : highRisk.slice(0, 6).map((asset) => {
                const score = asset.risk_score;
                const level = score != null && score >= 70 ? "high" : score != null && score >= 40 ? "medium" : "low";
                return (
                  <li key={asset.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 py-3 first:pt-0">
                    <div className="min-w-0"><p className="truncate text-sm font-medium">{asset.name ?? asset.id}</p><p className="mt-1 text-xs text-muted-foreground">{asset.id} Â· {asset.district ?? "District N/A"}</p><p className="mt-1 font-mono text-[11px] text-muted-foreground">Confidence {asset.confidence_score != null ? `${Math.round(asset.confidence_score * 100)}%` : "N/A"}</p></div>
                    <div className="text-right"><RiskBadge risk={level} /><p className="mt-2 text-sm font-semibold">{score != null ? score.toFixed(1) : "N/A"}</p></div>
                  </li>
                );
              })}
            </ul>
          </ChartCard>
        </div>

        <section aria-label="Quick actions" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {quickActions.map((item) => (
            <Link key={item.to} to={item.to} className="group flex items-center gap-3 rounded-lg border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-secondary">
              <span className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/20 bg-primary/8 text-primary"><item.icon className="size-4" /></span>
              <span className="truncate text-sm font-medium">{item.label}</span>
            </Link>
          ))}
        </section>
      </div>
    </DashboardLayout>
  );
}

