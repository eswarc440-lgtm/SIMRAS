import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Database, Download, FileSpreadsheet, FileText, ShieldCheck } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { EmptyState, PageHeader } from "../../components/common/PageHeader";
import { Button } from "../../components/ui/button";
import { API_BASE_URL, apiRequest } from "../../services/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

type ReportTemplate = {
  id: string;
  title: string;
  category: string;
  format: "PDF" | "CSV" | "XLSX" | string;
  requires_asset?: boolean;
  requires_district?: boolean;
  description: string;
};

type Asset = {
  asset_id?: string;
  asset_code?: string;
  name?: string;
  asset_type?: string;
  district?: string;
};

const categories = [
  "All",
  "Asset Condition",
  "Inspection",
  "Maintenance",
  "Risk",
  "AI Prediction",
  "Infrastructure",
  "Analytics",
  "Digital Twin",
  "Model Governance",
] as const;

function reportIcon(format: string) {
  if (format === "XLSX") return FileSpreadsheet;
  if (format === "CSV") return Database;
  return FileText;
}

function buildDownloadPath(report: ReportTemplate, assetId: string, district: string) {
  switch (report.id) {
    case "asset_condition":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/pdf`;
    case "inspection":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/inspection/pdf`;
    case "maintenance":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/maintenance/pdf`;
    case "risk":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/risk/pdf`;
    case "ai_prediction":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/ai/pdf`;
    case "twin_evidence":
      return `/api/v1/reports/asset/${encodeURIComponent(assetId)}/twin-evidence/pdf`;
    case "high_risk":
      return "/api/v1/reports/high-risk/csv";
    case "asset_register":
      return "/api/v1/reports/assets/csv";
    case "district_analytics":
      return `/api/v1/reports/district/${encodeURIComponent(district)}/pdf`;
    case "model_governance":
      return "/api/v1/reports/model-governance/pdf";
    case "portfolio":
      return "/api/v1/reports/portfolio/pdf";
    case "summary_xlsx":
      return "/api/v1/reports/summary/xlsx";
    default:
      throw new Error("Unsupported report type");
  }
}

function filenameFromResponse(response: Response, report: ReportTemplate) {
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  if (match?.[1]) return match[1];
  const ext = report.format.toLowerCase();
  return `simras-${report.id}.${ext}`;
}

export function ReportsPage() {
  const [category, setCategory] = useState<(typeof categories)[number]>("All");
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedReportId, setSelectedReportId] = useState("");
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<{ items?: ReportTemplate[] }>("/api/v1/reports/catalog"),
      apiRequest<{ items?: Asset[] }>("/api/v1/infrastructure?limit=500"),
    ])
      .then(([catalog, infrastructure]) => {
        setTemplates(catalog.items ?? []);
        setAssets(infrastructure.items ?? []);
      })
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => setLoading(false));
  }, []);

  const selectedTemplate = templates.find((item: any) => item.id === selectedReportId);
  const districts = useMemo(
    () => Array.from(new Set(assets.map((asset) => asset.district).filter((value): value is string => Boolean(value)))).sort(),
    [assets],
  );
  const rows = templates.filter((report) => category === "All" || report.category === category);

  const openGenerator = (reportId?: string) => {
    if (reportId) setSelectedReportId(reportId);
    setDialogOpen(true);
  };

  const canGenerate = Boolean(
    selectedTemplate &&
      (!selectedTemplate.requires_asset || selectedAssetId) &&
      (!selectedTemplate.requires_district || selectedDistrict),
  );

  const handleGenerateReport = async () => {
    if (!selectedTemplate || !canGenerate) return;
    setIsGenerating(true);
    setError(null);
    try {
      const path = buildDownloadPath(selectedTemplate, selectedAssetId, selectedDistrict);
      const response = await fetch(`${API_BASE_URL}${path}`, { headers: { Accept: "*/*" } });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Report generation failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filenameFromResponse(response, selectedTemplate);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setDialogOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Reports"
          title="Evidence-Backed Infrastructure Reports"
          description="Every report is generated on demand from the current SIMRAS backend and PostgreSQL/PostGIS records. Missing values remain N/A or withheld."
          actions={
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => openGenerator()}>Generate Report</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Generate Live Report</DialogTitle>
                  <DialogDescription>No frontend demonstration dataset is used.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Report</Label>
                    <Select value={selectedReportId} onValueChange={setSelectedReportId}>
                      <SelectTrigger><SelectValue placeholder="Select report..." /></SelectTrigger>
                      <SelectContent>
                        {templates.map((report) => (
                          <SelectItem key={report.id} value={report.id}>{report.title} Â· {report.format}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedTemplate?.requires_asset && (
                    <div className="space-y-2">
                      <Label>Asset</Label>
                      <Select value={selectedAssetId} onValueChange={setSelectedAssetId}>
                        <SelectTrigger><SelectValue placeholder="Select real asset..." /></SelectTrigger>
                        <SelectContent>
                          {assets.map((asset) => {
                            const code = asset.asset_code ?? asset.asset_id ?? "";
                            return <SelectItem key={code} value={code}>{code} Â· {asset.name ?? asset.asset_type ?? "Asset"}</SelectItem>;
                          })}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {selectedTemplate?.requires_district && (
                    <div className="space-y-2">
                      <Label>District</Label>
                      <Select value={selectedDistrict} onValueChange={setSelectedDistrict}>
                        <SelectTrigger><SelectValue placeholder="Select district..." /></SelectTrigger>
                        <SelectContent>
                          {districts.map((district) => <SelectItem key={district} value={district}>{district}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {selectedTemplate && (
                    <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                      {selectedTemplate.description}
                    </div>
                  )}

                  {error && <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}

                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={isGenerating}>Cancel</Button>
                    <Button onClick={handleGenerateReport} disabled={!canGenerate || isGenerating}>
                      <Download className="size-4" />
                      {isGenerating ? "Generating..." : "Generate from Database"}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          }
        />

        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 size-5 text-primary" />
            <div><strong>Real-data reporting enabled.</strong><p className="mt-1 text-muted-foreground">Cards below are report templates, not fabricated report history. Generated files query the live database at request time.</p></div>
          </div>
        </div>

        <nav className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <div className="flex min-w-max gap-2">
            {categories.map((item) => (
              <button key={item} type="button" onClick={() => setCategory(item)} className={`rounded-full border px-3.5 py-1.5 text-sm ${category === item ? "border-primary bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>{item}</button>
            ))}
          </div>
        </nav>

        {loading ? (
          <div className="rounded-lg border bg-card p-8 text-sm text-muted-foreground">Loading live report catalog...</div>
        ) : error && templates.length === 0 ? (
          <EmptyState title="Reports backend unavailable" description={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="No report templates in this category" />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {rows.map((report) => {
              const Icon = reportIcon(report.format);
              return (
                <article key={report.id} className="flex h-full flex-col rounded-lg border bg-card p-5 shadow-panel">
                  <div className="flex items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-md border border-primary/20 bg-primary/8 text-primary"><Icon className="size-4" /></span>
                    <div className="min-w-0"><h2 className="text-sm font-semibold">{report.title}</h2><p className="mt-1 text-[11px] text-muted-foreground">{report.category} Â· {report.format}</p></div>
                  </div>
                  <p className="mt-4 flex-1 text-sm text-muted-foreground">{report.description}</p>
                  <div className="mt-5 flex gap-2 border-t pt-4">
                    <Button asChild size="sm" variant="outline" className="flex-1"><Link to="/reports/$id" params={{ id: report.id }}>Details</Link></Button>
                    <Button size="sm" className="flex-1" onClick={() => openGenerator(report.id)}><Download className="size-4" />Generate</Button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export function ReportDetailsPage({ id }: { id: string }) {
  const [report, setReport] = useState<ReportTemplate | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<{ items?: ReportTemplate[] }>("/api/v1/reports/catalog")
      .then((payload: any) => setReport((payload.items ?? []).find((item: any) => item.id === id) ?? null))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/reports" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" />Back to Reports</Link>
        {loading ? (
          <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">Loading report definition...</div>
        ) : !report ? (
          <EmptyState title="Report type not found" description={`No live report template matches ${id}.`} />
        ) : (
          <>
            <PageHeader eyebrow={report.category} title={report.title} description={report.description} />
            <div className="rounded-lg border bg-card p-6">
              <dl className="grid gap-4 sm:grid-cols-3">
                <div><dt className="text-xs text-muted-foreground">Format</dt><dd className="mt-1 font-medium">{report.format}</dd></div>
                <div><dt className="text-xs text-muted-foreground">Scope</dt><dd className="mt-1 font-medium">{report.requires_asset ? "Selected asset" : report.requires_district ? "Selected district" : "Portfolio"}</dd></div>
                <div><dt className="text-xs text-muted-foreground">Data source</dt><dd className="mt-1 font-medium">FastAPI â†’ PostgreSQL/PostGIS</dd></div>
              </dl>
              <p className="mt-6 text-sm text-muted-foreground">Generate this report from the Reports page. No stored mock report body, fake page count or fabricated generated date is displayed.</p>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}


