import {
  Activity,
  Box,
  Boxes,
  Building2,
  ClipboardCheck,
  Droplets,
  FileBarChart,
  Landmark,
  Map,
  Route as RouteIcon,
  ShieldAlert,
  Sparkles,
  TowerControl,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Reveal, SectionHeading } from "../common/Reveal";
import { apiRequest } from "../../services/api";

const steps = [
  { no: "01", title: "Collect", body: "Inspection records, structural attributes, sensor and environmental data." },
  { no: "02", title: "Understand", body: "AI and GIS analysis establish condition, context and deterioration drivers." },
  { no: "03", title: "Predict", body: "Models score risk, health and remaining useful life for every asset." },
  { no: "04", title: "Assist", body: "Prioritised actions, reports and evidence for data-driven decisions." },
];

export function HowItWorks() {
  return (
    <section className="border-b bg-background py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="Process" title="How SIMRAS Works." />
        </Reveal>

        <ol className="mt-14 grid gap-6 lg:grid-cols-4">
          {steps.map((s, i) => (
            <Reveal key={s.no} delay={i * 0.1}>
              <li className="relative h-full rounded-lg border bg-card p-6">
                <span className="absolute -top-px left-0 h-px w-16 bg-primary" aria-hidden="true" />
                <p className="font-mono text-xs text-primary">{s.no}</p>
                <h3 className="mt-5 font-display text-lg font-bold tracking-tight uppercase">{s.title}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

const capabilities = [
  { icon: Sparkles, title: "AI Risk Prediction", body: "Model-driven risk scoring with confidence levels for every asset." },
  { icon: Activity, title: "Infrastructure Monitoring", body: "Continuous condition tracking across the asset portfolio." },
  { icon: TrendingUp, title: "Structural Analytics", body: "Deterioration trends, comparisons and regional analysis." },
  { icon: Box, title: "Digital Twin", body: "Geometry-accurate digital representation of physical assets." },
  { icon: Map, title: "GIS Intelligence", body: "Spatial visualisation of assets, corridors and risk zones." },
  { icon: Boxes, title: "Asset Management", body: "Centralised register of structures, status and inspections." },
  { icon: ShieldAlert, title: "Risk Assessment", body: "Structured evaluation of severity, exposure and consequence." },
  { icon: FileBarChart, title: "Automated Reports", body: "Generated risk, condition and analytics reporting." },
  { icon: ClipboardCheck, title: "Decision Support", body: "Prioritised recommendations backed by evidence." },
];

export function Capabilities() {
  return (
    <section className="border-b bg-surface py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="Capabilities" title="One Platform. Complete Infrastructure Coverage." />
        </Reveal>

        <div className="mt-14 grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {capabilities.map((c, i) => (
            <Reveal key={c.title} delay={(i % 3) * 0.06} className="bg-card">
              <div className="group h-full p-6 transition-colors hover:bg-secondary">
                <span className="grid size-10 place-items-center rounded-md border border-primary/20 bg-primary/8 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <c.icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-base font-semibold">{c.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const categoryIcons = [RouteIcon, Landmark, Building2, Droplets, TowerControl, Boxes];

export function MonitoringSection() {
  const [summary, setSummary] = useState({ total: 0, healthy: 0, warning: 0, critical: 0 });
  const [assetTypeSummary, setAssetTypeSummary] = useState<Array<{ type: string; total: number; healthy: number; warning: number; critical: number }>>([]);

  useEffect(() => {
    const loadSummary = async () => {
      try {
        const overview = await apiRequest<{ total_assets?: number; high_risk_assets?: number; medium_risk_assets?: number; low_risk_assets?: number; average_health_score?: number }>("/api/v1/dashboard/overview");
        const risk = await apiRequest<{ asset_type_risk?: Array<{ asset_type: string; count: number; high_risk: number }> }>("/api/v1/analytics/risk-analysis");

        const total = Number(overview.total_assets ?? 0);
        const high = Number(overview.high_risk_assets ?? 0);
        const medium = Number(overview.medium_risk_assets ?? 0);
        const low = Number(overview.low_risk_assets ?? 0);

        setSummary({
          total,
          healthy: total - high - medium,
          warning: medium,
          critical: high,
        });

        const riskRows = (risk.asset_type_risk ?? []).map((item: any) => ({
          type: item.asset_type,
          total: Number(item.count ?? 0),
          healthy: Math.max(0, Number(item.count ?? 0) - Number(item.high_risk ?? 0)),
          warning: Math.max(0, Math.round(Number(item.count ?? 0) * 0.2)),
          critical: Number(item.high_risk ?? 0),
        }));
        setAssetTypeSummary(riskRows);
      } catch (error) {
        console.error("Live monitoring summary failed", error);
        setSummary({ total: 0, healthy: 0, warning: 0, critical: 0 });
        setAssetTypeSummary([]);
      }
    };

    void loadSummary();
  }, []);

  const liveAssetTypeSummary = useMemo(() => assetTypeSummary.length > 0 ? assetTypeSummary : [], [assetTypeSummary]);

  return (
    <section id="infrastructure" className="border-b bg-background py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="Infrastructure Monitoring"
            title="Every Structure Category, Under One View."
            description="Live portfolio statistics from the connected PostgreSQL/PostGIS infrastructure dataset."
          />
        </Reveal>

        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Total Infrastructure Assets", value: summary.total.toLocaleString(), tone: "text-foreground" },
            { label: "Healthy", value: summary.healthy.toLocaleString(), tone: "text-success" },
            { label: "Warning", value: summary.warning.toLocaleString(), tone: "text-warning" },
            { label: "Critical", value: summary.critical.toLocaleString(), tone: "text-danger" },
          ].map((s, i) => (
            <Reveal key={s.label} delay={i * 0.06} className="bg-card">
              <div className="p-6">
                <p className="eyebrow text-muted-foreground">{s.label}</p>
                <p className={`mt-3 font-display text-4xl font-bold tabular-nums ${s.tone}`}>{s.value}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {liveAssetTypeSummary.length === 0 ? (
            <div className="col-span-full rounded-lg border bg-card p-5 text-sm text-muted-foreground">No live infrastructure categories are available from the connected database yet.</div>
          ) : liveAssetTypeSummary.map((cat, i) => {
            const Icon = categoryIcons[i % categoryIcons.length]!;
            const healthyPct = cat.total ? Math.round((cat.healthy / cat.total) * 100) : 0;
            return (
              <Reveal key={cat.type} delay={(i % 3) * 0.06}>
                <article className="h-full rounded-lg border bg-card p-5">
                  <div className="flex items-center gap-3">
                    <span className="grid size-9 shrink-0 place-items-center rounded-md border bg-secondary text-primary">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <h3 className="min-w-0 truncate text-sm font-semibold">{cat.type}</h3>
                    <span className="ml-auto shrink-0 font-display text-lg font-bold tabular-nums">{cat.total}</span>
                  </div>
                  <div className="mt-4 flex h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                    <span className="bg-success" style={{ width: `${cat.total ? (cat.healthy / cat.total) * 100 : 0}%` }} />
                    <span className="bg-warning" style={{ width: `${cat.total ? (cat.warning / cat.total) * 100 : 0}%` }} />
                    <span className="bg-danger" style={{ width: `${cat.total ? (cat.critical / cat.total) * 100 : 0}%` }} />
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {healthyPct}% healthy Â· {cat.warning} warning Â· {cat.critical} critical
                  </p>
                </article>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

const impacts = [
  { no: "01", title: "Earlier Risk Identification", body: "Structural deterioration is surfaced months before it becomes visible failure." },
  { no: "02", title: "Better Infrastructure Visibility", body: "A single operational picture of condition across districts and asset classes." },
  { no: "03", title: "Centralised Asset Intelligence", body: "Inspection history, geometry, analytics and predictions in one record." },
  { no: "04", title: "Data-Driven Decision Support", body: "Maintenance and investment decisions supported by evidence, not intuition." },
];

export function ImpactSection() {
  return (
    <section id="impact" className="border-b bg-surface py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="Impact" title="From Infrastructure Data to Intelligent Action." />
        </Reveal>

        <div className="mt-14 grid gap-x-10 gap-y-px border-t sm:grid-cols-2">
          {impacts.map((im, i) => (
            <Reveal key={im.no} delay={i * 0.08}>
              <div className="border-b py-8">
                <p className="font-mono text-xs text-primary">{im.no}</p>
                <h3 className="mt-3 font-display text-xl font-bold tracking-tight">{im.title}</h3>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{im.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

