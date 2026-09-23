import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Download, FileCheck2, ShieldCheck } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { EmptyState, PageHeader } from "../../components/common/PageHeader";
import { Button } from "../../components/ui/button";
import { API_BASE_URL, apiRequest } from "../../services/api";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { displayableReportEntries, labelForReportKey } from "./realReportPresentation";

type Asset = {
  asset_id?: string;
  asset_code?: string;
  name?: string;
  asset_type?: string;
  district?: string;
};

type RealReport = {
  asset_code: string;
  asset?: Record<string, unknown>;
  official_asset_facts?: Record<string, unknown>;
  government_engineering?: Record<string, unknown>;
  digital_twin?: Record<string, unknown>;
  real_environment_observations?: Record<string, Record<string, unknown>>;
  real_inspection?: Record<string, unknown>;
  real_maintenance?: Record<string, unknown>[];
  ml_prediction?: Record<string, unknown>;
  evidence?: Record<string, unknown>;
  generated_at?: string;
};

const HIGH_FIDELITY_PRIORITY = new Map<string, number>([
  ["AP_DAM_00002", 0],
  ["AP_DAM_00001", 1],
  ["AP_BAR_WRIS_B00131", 2],
  ["AP_DAM_NWDP_AP01VH0059", 3],
  ["AP_DAM_WRIS_AP01HH0062", 4],
  ["AP_AIR_VOBZ", 5],
  ["AP_AIR_VOTP", 6],
  ["AP_TEMPLE_TTD_0001", 7],
]);

function codeOf(asset: Asset) {
  return asset.asset_code ?? asset.asset_id ?? "";
}

function priorityOf(asset: Asset) {
  return HIGH_FIDELITY_PRIORITY.get(codeOf(asset)) ?? 1000;
}

function EvidenceTable({ title, data }: { title: string; data?: Record<string, unknown> }) {
  const rows = displayableReportEntries(data);
  if (rows.length === 0) return null;
  return (
    <section className="overflow-hidden rounded-xl border bg-card shadow-panel">
      <div className="border-b bg-muted/20 px-5 py-4">
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <dl className="divide-y">
        {rows.map(([label, value]) => (
          <div key={`${title}-${label}`} className="grid gap-1 px-5 py-3 sm:grid-cols-[220px_1fr] sm:gap-5">
            <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
            <dd className="break-words text-sm font-semibold text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function EnvironmentSection({ data }: { data?: Record<string, Record<string, unknown>> }) {
  const items = Object.entries(data ?? {}).filter(([, value]) => displayableReportEntries(value).length > 0);
  if (items.length === 0) return null;
  return (
    <section className="rounded-xl border bg-card p-5 shadow-panel">
      <h2 className="text-sm font-semibold">Current Real Environment Observations</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map(([name, value]) => (
          <article key={name} className="rounded-lg border bg-muted/10 p-3">
            <div className="text-xs font-semibold">{labelForReportKey(name)}</div>
            <dl className="mt-2 space-y-1.5">
              {displayableReportEntries(value).map(([label, text]) => (
                <div key={`${name}-${label}`} className="flex items-start justify-between gap-3 text-xs">
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="text-right font-medium">{text}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

function MaintenanceSection({ rows }: { rows?: Record<string, unknown>[] }) {
  const records = (rows ?? []).filter((row) => displayableReportEntries(row).length > 0);
  if (records.length === 0) return null;
  return (
    <section className="rounded-xl border bg-card p-5 shadow-panel">
      <h2 className="text-sm font-semibold">Verified Maintenance Records</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {records.map((row, index) => (
          <dl key={`maintenance-${index}`} className="rounded-lg border p-3">
            {displayableReportEntries(row).map(([label, value]) => (
              <div key={`${index}-${label}`} className="mb-2 grid grid-cols-[130px_1fr] gap-3 text-xs last:mb-0">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        ))}
      </div>
    </section>
  );
}

export function ReportsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetCode, setSelectedAssetCode] = useState("");
  const [report, setReport] = useState<RealReport | null>(null);
  const [loadingAssets, setLoadingAssets] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<{ items?: Asset[] }>("/api/v1/infrastructure?limit=500")
      .then((payload) => {
        const sorted = [...(payload.items ?? [])].sort((a, b) => {
          const priority = priorityOf(a) - priorityOf(b);
          if (priority !== 0) return priority;
          return String(a.name ?? codeOf(a)).localeCompare(String(b.name ?? codeOf(b)));
        });
        setAssets(sorted);
        const first = sorted.find((asset) => HIGH_FIDELITY_PRIORITY.has(codeOf(asset))) ?? sorted[0];
        if (first) setSelectedAssetCode(codeOf(first));
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
      .finally(() => setLoadingAssets(false));
  }, []);

  useEffect(() => {
    if (!selectedAssetCode) {
      setReport(null);
      return;
    }
    setLoadingReport(true);
    setError(null);
    apiRequest<RealReport>(`/api/v1/real-reports/${encodeURIComponent(selectedAssetCode)}`)
      .then(setReport)
      .catch((reason) => {
        setReport(null);
        setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => setLoadingReport(false));
  }, [selectedAssetCode]);

  const selectedAsset = useMemo(
    () => assets.find((asset) => codeOf(asset) === selectedAssetCode),
    [assets, selectedAssetCode],
  );

  const hasGovernmentEvidence = displayableReportEntries(report?.government_engineering).length > 0;

  const downloadPdf = async () => {
    if (!selectedAssetCode) return;
    setDownloading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/real-reports/${encodeURIComponent(selectedAssetCode)}/pdf`,
        { headers: { Accept: "application/pdf" } },
      );
      if (!response.ok) throw new Error(`Report generation failed (${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `SIMRAS_${selectedAssetCode}_REAL_REPORT.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Reports"
          title="Real Infrastructure Evidence Report"
          description="Selected-asset reports show only source-backed facts, real observations and eligible validated ML results. Empty or insufficient fields are omitted completely."
          actions={
            <Button onClick={downloadPdf} disabled={!report || downloading}>
              <Download className="size-4" />
              {downloading ? "Generating..." : "Download Real PDF"}
            </Button>
          }
        />

        <div className="grid gap-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4 md:grid-cols-[1fr_auto] md:items-end">
          <div className="space-y-2">
            <Label>Infrastructure asset</Label>
            <Select value={selectedAssetCode} onValueChange={setSelectedAssetCode} disabled={loadingAssets}>
              <SelectTrigger className="max-w-2xl"><SelectValue placeholder="Select infrastructure..." /></SelectTrigger>
              <SelectContent>
                {assets.map((asset) => {
                  const code = codeOf(asset);
                  const priority = HIGH_FIDELITY_PRIORITY.has(code);
                  return (
                    <SelectItem key={code} value={code}>
                      {priority ? "★ " : ""}{code} · {asset.name ?? asset.asset_type ?? "Infrastructure"}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">★ Source-backed high-fidelity twins are placed first.</p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-background px-3 py-2 text-xs font-semibold text-emerald-600 dark:text-emerald-300">
            <ShieldCheck className="size-4" />
            REAL EVIDENCE ONLY
          </div>
        </div>

        {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>}

        {loadingReport ? (
          <div className="rounded-xl border bg-card p-8 text-sm text-muted-foreground">Loading verified evidence...</div>
        ) : !report ? (
          <EmptyState title="Select an infrastructure asset" description="The report appears when verified evidence is returned by SIMRAS." />
        ) : (
          <>
            <section className="rounded-xl border bg-card p-5 shadow-panel">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-cyan-600">Selected asset</div>
                  <h2 className="mt-1 text-xl font-semibold">{String(report.asset?.name ?? selectedAsset?.name ?? selectedAssetCode)}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{selectedAssetCode}{selectedAsset?.district ? ` · ${selectedAsset.district}` : ""}</p>
                </div>
                {hasGovernmentEvidence && (
                  <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                    <FileCheck2 className="size-3.5" /> Government / authoritative engineering evidence
                  </span>
                )}
              </div>
            </section>

            <EvidenceTable title="Asset Identity" data={report.asset} />
            <EvidenceTable title="Official Asset Facts" data={report.official_asset_facts} />
            <EvidenceTable title="Government / Authoritative Engineering Evidence" data={report.government_engineering} />
            <EvidenceTable title="Digital Twin Provenance" data={report.digital_twin} />
            <EnvironmentSection data={report.real_environment_observations} />
            <EvidenceTable title="Latest Real Inspection" data={report.real_inspection} />
            <MaintenanceSection rows={report.real_maintenance} />
            <EvidenceTable title="Eligible Locally Validated ML Prediction" data={report.ml_prediction} />
            <EvidenceTable title="Evidence Provenance" data={report.evidence} />
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

export function ReportDetailsPage({ id }: { id: string }) {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/reports" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" /> Back to Reports
        </Link>
        <PageHeader
          eyebrow="Evidence-backed report"
          title="Selected Asset Real Report"
          description="SIMRAS now generates one clear selected-asset report from available authoritative engineering evidence, real observations and eligible validated ML outputs."
        />
        <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
          Open the Reports page, select the infrastructure asset, review the live evidence, and download the PDF. Legacy template id: {id}.
        </div>
      </div>
    </DashboardLayout>
  );
}
