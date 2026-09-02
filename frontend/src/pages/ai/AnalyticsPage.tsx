import { useEffect, useState } from "react";
import { Download, FileBarChart } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Pie, PieChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, PageHeader } from "../../components/common/PageHeader";
import { AITabs } from "../../components/ai/AITabs";
import { Button } from "../../components/ui/button";
import { API_BASE_URL, apiRequest } from "../../services/api";

const tooltipStyle = { background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 };
const riskColors = ["var(--color-success)", "var(--color-warning)", "var(--color-danger)"];

export function AnalyticsPage() {
  const [overview, setOverview] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);

  useEffect(() => {
    apiRequest<any>("/api/v1/dashboard/overview").then(setOverview).catch(() => setOverview(null));
    apiRequest<any>("/api/v1/analytics/risk-analysis").then(setRisk).catch(() => setRisk(null));
  }, []);

  const riskDistribution = overview?.risk_distribution ?? [];
  const districts = risk?.district_risk ?? [];
  const assetTypes = risk?.asset_type_risk ?? [];

  const download = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/reports/summary/xlsx`);
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "simras-summary.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="AI Intelligence"
          title="Analytics"
          description="Current portfolio analytics calculated from live asset and prediction records. No synthetic trends or fabricated category splits are displayed."
          actions={<><Button variant="outline" onClick={download}><Download className="size-4" />Export Live Summary</Button><Button asChild><a href="/reports"><FileBarChart className="size-4" />Reports</a></Button></>}
        />
        <AITabs />

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="Risk Distribution" subtitle="Current stored classifications">
            <div className="h-72">{riskDistribution.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%">{riskDistribution.map((entry: any, index: number) => <Cell key={entry.key} fill={riskColors[index % riskColors.length]} />)}</Pie><Legend wrapperStyle={{ fontSize: 12 }} /><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No stored risk data available.</div>}</div>
          </ChartCard>

          <ChartCard title="District Analysis" subtitle="Real asset and risk counts by district">
            <div className="h-72">{districts.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={districts.slice(0, 15)} margin={{ left: -12, right: 8, top: 8 }}><CartesianGrid stroke="var(--color-border)" vertical={false} /><XAxis dataKey="district" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} interval={0} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} /><Bar dataKey="assets" name="Assets" fill="var(--color-chart-1)" /><Bar dataKey="high_risk" name="High risk" fill="var(--color-danger)" /></BarChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No district analytics available.</div>}</div>
          </ChartCard>

          <ChartCard title="Asset Type Analysis" subtitle="Real asset counts and high-risk counts by type">
            <div className="h-72">{assetTypes.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={assetTypes.slice(0, 15)} margin={{ left: -12, right: 8, top: 8 }}><CartesianGrid stroke="var(--color-border)" vertical={false} /><XAxis dataKey="asset_type" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} interval={0} /><YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} /><Bar dataKey="assets" name="Assets" fill="var(--color-chart-2)" /><Bar dataKey="high_risk" name="High risk" fill="var(--color-danger)" /></BarChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No asset-type analytics available.</div>}</div>
          </ChartCard>

          <ChartCard title="Portfolio Coverage" subtitle="Current stored evidence coverage">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-md border bg-surface p-4"><dt className="text-xs text-muted-foreground">Total assets</dt><dd className="mt-2 text-2xl font-bold">{overview?.total_assets ?? "N/A"}</dd></div>
              <div className="rounded-md border bg-surface p-4"><dt className="text-xs text-muted-foreground">Stored predictions</dt><dd className="mt-2 text-2xl font-bold">{overview?.total_predictions ?? "N/A"}</dd></div>
              <div className="rounded-md border bg-surface p-4"><dt className="text-xs text-muted-foreground">Average health</dt><dd className="mt-2 text-2xl font-bold">{overview?.average_health_score != null ? overview.average_health_score.toFixed(1) : "N/A"}</dd></div>
              <div className="rounded-md border bg-surface p-4"><dt className="text-xs text-muted-foreground">Average risk</dt><dd className="mt-2 text-2xl font-bold">{overview?.average_risk_score != null ? overview.average_risk_score.toFixed(1) : "N/A"}</dd></div>
            </dl>
          </ChartCard>
        </div>
      </div>
    </DashboardLayout>
  );
}
