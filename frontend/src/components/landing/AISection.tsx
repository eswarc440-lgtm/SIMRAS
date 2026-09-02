import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Reveal, SectionHeading } from "../common/Reveal";
import { apiRequest } from "../../services/api";

type Overview = {
  total_assets?: number;
  total_predictions?: number;
  high_risk_assets?: number;
  risk_distribution?: Array<{ key: string; name: string; value: number }>;
  top_high_risk_assets?: Array<{
    id: string;
    name?: string;
    district?: string;
    risk_score?: number | null;
    confidence_score?: number | null;
  }>;
};

type ModelStatus = Record<string, unknown>;

function modelStage(payload: ModelStatus | null) {
  if (!payload) return "N/A";
  const candidates = [
    payload.stage,
    (payload.model as Record<string, unknown> | undefined)?.stage,
    (payload.current as Record<string, unknown> | undefined)?.stage,
    ((payload.items as Array<Record<string, unknown>> | undefined) ?? [])[0]?.stage,
    ((payload.models as Array<Record<string, unknown>> | undefined) ?? [])[0]?.stage,
  ];
  const value = candidates.find((item) => typeof item === "string");
  return typeof value === "string" ? value.replaceAll("_", " ") : "N/A";
}

export function AISection() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);

  useEffect(() => {
    apiRequest<Overview>("/api/v1/dashboard/overview").then(setOverview).catch(() => setOverview(null));
    apiRequest<ModelStatus>("/api/v1/analytics/models/status").then(setModel).catch(() => setModel(null));
  }, []);

  const riskDistribution = useMemo(
    () => overview?.risk_distribution ?? [],
    [overview],
  );
  const top = overview?.top_high_risk_assets?.[0];
  const stats = [
    { label: "Model Stage", value: modelStage(model) },
    { label: "Stored Predictions", value: overview?.total_predictions != null ? overview.total_predictions.toLocaleString() : "N/A" },
    { label: "High Risk Assets", value: overview?.high_risk_assets != null ? overview.high_risk_assets.toLocaleString() : "N/A" },
    { label: "Monitored Assets", value: overview?.total_assets != null ? overview.total_assets.toLocaleString() : "N/A" },
  ];

  return (
    <section id="ai" className="relative overflow-hidden border-b bg-navy py-20 text-navy-foreground sm:py-28">
      <div className="grid-lines absolute inset-0 opacity-[0.05]" aria-hidden="true" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="AI Intelligence"
            tone="light"
            title="Decision Support From Stored Infrastructure Evidence."
            description="SIMRAS displays only backend prediction records and model-governance state. Unavailable or withheld outputs remain explicitly unavailable."
          />
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-14 overflow-hidden rounded-xl border border-navy-foreground/12 bg-navy-foreground/[0.03] shadow-elevated backdrop-blur-sm">
            <div className="flex items-center justify-between gap-3 border-b border-navy-foreground/10 px-5 py-3.5">
              <p className="eyebrow text-accent">AI Intelligence</p>
              <p className="font-mono text-[11px] text-navy-foreground/45">LIVE BACKEND DATA</p>
            </div>

            <div className="grid gap-px bg-navy-foreground/10 sm:grid-cols-2 lg:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="bg-navy px-5 py-5">
                  <p className="eyebrow text-navy-foreground/45">{stat.label}</p>
                  <p className="mt-2 break-words font-display text-xl font-bold tabular-nums">{stat.value}</p>
                </div>
              ))}
            </div>

            <div className="grid gap-px bg-navy-foreground/10 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
              <div className="bg-navy p-5">
                <p className="text-sm font-semibold">Current Risk Distribution</p>
                <div className="mt-4 h-56">
                  {riskDistribution.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={riskDistribution} margin={{ left: -18, right: 6, top: 6 }}>
                        <CartesianGrid stroke="var(--color-sidebar-border)" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "currentColor" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "currentColor" }} axisLine={false} tickLine={false} />
                        <Tooltip
                          cursor={{ fill: "var(--color-sidebar-accent)" }}
                          contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8, color: "var(--color-card-foreground)", fontSize: 12 }}
                        />
                        <Bar dataKey="value" name="Assets" fill="var(--color-chart-2)" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="grid h-full place-items-center text-sm text-navy-foreground/50">No stored risk classification data available.</div>
                  )}
                </div>
              </div>

              <div className="bg-navy p-5">
                <p className="text-sm font-semibold">Highest Current Stored Risk</p>
                {top ? (
                  <div className="mt-5 space-y-4">
                    <div><p className="eyebrow text-navy-foreground/45">Asset</p><p className="mt-1 font-semibold">{top.name ?? top.id}</p><p className="mt-1 text-xs text-navy-foreground/55">{top.id} · {top.district ?? "District N/A"}</p></div>
                    <div className="grid grid-cols-2 gap-4">
                      <div><p className="eyebrow text-navy-foreground/45">Risk Score</p><p className="mt-1 text-xl font-bold">{top.risk_score != null ? top.risk_score.toFixed(1) : "N/A"}</p></div>
                      <div><p className="eyebrow text-navy-foreground/45">Confidence</p><p className="mt-1 text-xl font-bold">{top.confidence_score != null ? `${Math.round(top.confidence_score * 100)}%` : "N/A"}</p></div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-md border border-navy-foreground/10 p-4 text-sm text-navy-foreground/55">No high-risk stored prediction is currently available.</div>
                )}
              </div>
            </div>

            <div className="border-t border-navy-foreground/10 bg-navy p-5 text-xs text-navy-foreground/55">
              Prediction values are decision-support outputs. Model stage and unavailable values are shown without frontend fabrication.
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
