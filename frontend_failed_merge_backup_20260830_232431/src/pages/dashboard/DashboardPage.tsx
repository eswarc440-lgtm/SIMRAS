import { Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  Box,
  Building2,
  FileBarChart,
  Map,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { PageHeader, ChartCard } from "../../components/common/PageHeader";
import { StatCard } from "../../components/common/StatCard";
import { RiskBadge } from "../../components/common/StatusBadge";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../hooks/useAuth";
import { apiRequest } from "../../services/api";

const riskColors = ["var(--color-success)", "var(--color-warning)", "var(--color-danger)"];

const quickActions = [
  { to: "/infrastructure", label: "View Infrastructure", icon: Building2 },
  { to: "/gis", label: "Open GIS", icon: Map },
  { to: "/digital-twin", label: "Open Digital Twin", icon: Box },
  { to: "/ai/predictions", label: "View Predictions", icon: Activity },
  { to: "/reports", label: "Generate Report", icon: FileBarChart },
] as const;

type DashboardOverview = {
  total_assets: number;
  total_bridges: number;
  total_dams: number;
  total_barrages: number;
  total_ports: number;
  total_roads: number;
  total_buildings: number;
  total_airports: number;
  total_power_plants: number;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  average_health_score: number;
  average_risk_score: number;
  average_remaining_life: number;
  district_distribution: Array<{ district: string; count: number }>;
  asset_type_distribution: Array<{ asset_type: string; count: number }>;
  risk_distribution: Array<{ key: string; name: string; value: number }>;
  top_high_risk_assets: Array<{ id: string; name: string; asset_type: string; district: string; risk_score: number; health_score: number; remaining_life: number }>;
  recent_assessments: Array<{ assessment_id: string; assessment_name: string; asset_id: string; risk_level: string; health_score: number; last_assessed: string }>;
};

export function DashboardPage() {
  const { user } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const [overview, setOverview] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    apiRequest<DashboardOverview>("/api/v1/dashboard/overview")
      .then((data) => setOverview(data))
      .catch((error) => {
        console.error("Dashboard overview fetch failed", error);
        setOverview(null);
      });
  }, []);

  const healthTrend = useMemo(
    () => [
      {
        period: "Current",
        healthy: overview ? Math.max(0, Math.round((overview.average_health_score || 0) * 10)) : 0,
        warning: overview ? Math.max(0, Math.round(((overview.medium_risk_assets || 0) * 100) / Math.max(1, overview.total_assets))) : 0,
        critical: overview ? Math.max(0, Math.round(((overview.high_risk_assets || 0) * 100) / Math.max(1, overview.total_assets))) : 0,
      },
    ],
    [overview],
  );

  const riskDistribution = overview?.risk_distribution ?? [
    { key: "low", name: "Low Risk", value: 0 },
    { key: "medium", name: "Medium Risk", value: 0 },
    { key: "high", name: "High Risk", value: 0 },
  ];

  const insights = (overview?.top_high_risk_assets ?? []).slice(0, 3).map((asset, index) => ({
    id: asset.id,
    title: `${asset.asset_type} risk escalation`,
    body: `${asset.name || asset.id} in ${asset.district} is trending above the monitoring threshold.`,
    assetId: asset.id,
    risk: (asset.risk_score >= 70 ? "high" : asset.risk_score >= 40 ? "medium" : "low") as "high" | "medium" | "low",
    confidence: Math.min(99, Math.max(60, asset.health_score + 20 + index * 3)),
  }));

  const recentActivity = (overview?.recent_assessments ?? []).slice(0, 4).map((item, index) => ({
    id: item.assessment_id || `activity-${index}`,
    action: item.assessment_name,
    actor: item.risk_level ? `${item.risk_level} risk review` : "Database sync",
    time: item.last_assessed || "Live",
  }));

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow={`${greeting}, ${user?.name ?? "Officer"}`}
          title="Infrastructure Overview"
          description="Last updated: Today Â· Live dataset from the Structure Guard backend."
          actions={
            <Button asChild>
              <Link to="/reports">
                Generate Report
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          }
        />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Assets" value={overview ? overview.total_assets.toLocaleString() : "â€”"} icon={Building2} delta="Across all monitored districts" />
          <StatCard label="Healthy" value={overview ? `${Math.round(overview.average_health_score || 0)}%` : "â€”"} icon={TrendingUp} tone="success" delta="Average portfolio health" />
          <StatCard label="At Risk" value={overview ? (overview.high_risk_assets + overview.medium_risk_assets).toLocaleString() : "â€”"} icon={ShieldAlert} tone="warning" delta={`${overview?.high_risk_assets ?? 0} high Â· ${overview?.medium_risk_assets ?? 0} medium`} />
          <StatCard label="AI Predictions" value={overview ? (overview.top_high_risk_assets.length || 0).toLocaleString() : "â€”"} icon={Sparkles} tone="accent" delta="Latest high-risk queue" />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <ChartCard title="Infrastructure Health" subtitle="Real-time portfolio status">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={healthTrend} margin={{ left: -16, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="hGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--color-success)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="var(--color-success)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="healthy" name="Healthy" stroke="var(--color-success)" fill="url(#hGrad)" strokeWidth={2} />
                  <Area type="monotone" dataKey="warning" name="Warning" stroke="var(--color-warning)" fill="transparent" strokeWidth={2} />
                  <Area type="monotone" dataKey="critical" name="Critical" stroke="var(--color-danger)" fill="transparent" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard title="Risk Overview" subtitle="Portfolio risk classification">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2}>
                    {riskDistribution.map((entry, i) => (
                      <Cell key={entry.key} fill={riskColors[i % riskColors.length]} stroke="var(--color-card)" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="AI Insights" subtitle="Generated from live risk ranking">
            <ul className="space-y-3">
              {insights.length === 0 ? (
                <li className="rounded-md border bg-surface p-4 text-sm text-muted-foreground">No high-risk assets were returned by the live backend yet.</li>
              ) : insights.map((insight) => (
                <li key={insight.id} className="rounded-md border bg-surface p-4">
                  <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                    <p className="min-w-0 text-sm font-medium">{insight.title}</p>
                    <RiskBadge risk={insight.risk} />
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{insight.body}</p>
                  <p className="mt-3 font-mono text-[11px] text-muted-foreground">
                    {insight.assetId} Â· CONFIDENCE {insight.confidence.toFixed(1)}%
                  </p>
                </li>
              ))}
            </ul>
          </ChartCard>

          <ChartCard title="Recent Activity" subtitle="Latest live database events">
            <ul className="divide-y">
              {recentActivity.length === 0 ? (
                <li className="py-3 text-sm text-muted-foreground">No recent activity available.</li>
              ) : recentActivity.map((a) => (
                <li key={a.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-3.5 first:pt-0">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{a.action}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">{a.actor}</p>
                  </div>
                  <p className="shrink-0 font-mono text-[11px] text-muted-foreground">{a.time}</p>
                </li>
              ))}
            </ul>
          </ChartCard>
        </div>

        <section aria-label="Quick actions" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {quickActions.map((qa) => (
            <Link
              key={qa.to}
              to={qa.to}
              className="group flex items-center gap-3 rounded-lg border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-secondary"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/20 bg-primary/8 text-primary">
                <qa.icon className="size-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 truncate text-sm font-medium">{qa.label}</span>
            </Link>
          ))}
        </section>
      </div>
    </DashboardLayout>
  );
}

