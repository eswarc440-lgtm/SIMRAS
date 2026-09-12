import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Download, FileText, FileJson, File } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, EmptyState, PageHeader } from "../../components/common/PageHeader";
import { Button } from "../../components/ui/button";
import { apiRequest } from "../../services/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const categories = ["All", "AI Prediction", "Infrastructure", "Risk", "Analytics", "Inspection"] as const;
const reportTypes = [
  { id: "pdf", label: "PDF Report", icon: FileText },
  { id: "csv", label: "CSV Export", icon: FileJson },
  { id: "xlsx", label: "Excel Summary", icon: File },
] as const;

const statusTone: Record<string, string> = {
  Ready: "text-success",
  Processing: "text-warning",
  Archived: "text-muted-foreground",
};

interface InfrastructureAsset {
  asset_id: string;
  asset_type?: string;
  city?: string;
  state?: string;
  health_score?: number;
}

export function ReportsPage() {
  const [category, setCategory] = useState<(typeof categories)[number]>("All");
  const [reports, setReports] = useState<Array<{ id: string; title: string; category: string; type: string; generated: string; status: string; summary: string; pages: number }>>([]);
  const [assets, setAssets] = useState<InfrastructureAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>("");
  const [selectedReportType, setSelectedReportType] = useState<string>("pdf");
  const [isGenerating, setIsGenerating] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    apiRequest<{ recent_assessments?: Array<any>; top_high_risk_assets?: Array<any> }>('/api/v1/dashboard/overview')
      .then((payload) => {
        const source = payload.recent_assessments?.length
          ? payload.recent_assessments
          : (payload.top_high_risk_assets ?? []);
        const rows = source.map((item, index) => ({
          id: item.assessment_id || item.id || `report-${index}`,
          title: item.assessment_name || item.name || `Assessment ${index + 1}`,
          category: item.risk_level ? 'Risk' : 'Infrastructure',
          type: item.risk_level || 'Portfolio',
          generated: item.last_assessed || 'Live',
          status: 'Ready',
          summary: `${item.assessment_name || item.name || 'Asset'} is currently tracked with a ${Number(item.risk_score ?? 0).toFixed(1)} risk score and ${Number(item.health_score ?? 0).toFixed(0)} health score.`,
          pages: 8 + index,
        }));
        setReports(rows);
      })
      .catch((error) => console.error('Reports fetch failed', error));

    // Fetch assets for report generation
    apiRequest<{ items?: InfrastructureAsset[] }>('/api/v1/infrastructure?limit=100')
      .then((payload) => {
        setAssets(payload.items ?? []);
      })
      .catch((error) => console.error('Assets fetch failed', error));
  }, []);

  const handleGenerateReport = async () => {
    if (!selectedAssetId) {
      alert("Please select an asset");
      return;
    }

    setIsGenerating(true);
    try {
      let downloadUrl = "";
      let fileName = `report_${selectedAssetId}_${new Date().toISOString().split('T')[0]}`;

      if (selectedReportType === "pdf") {
        downloadUrl = `/api/v1/reports/asset/${selectedAssetId}/pdf`;
        fileName += ".pdf";
      } else if (selectedReportType === "csv") {
        downloadUrl = `/api/v1/reports/assets/csv`;
        fileName = `assets_${new Date().toISOString().split('T')[0]}.csv`;
      } else if (selectedReportType === "xlsx") {
        downloadUrl = `/api/v1/reports/summary/xlsx`;
        fileName = `simras_summary_${new Date().toISOString().split('T')[0]}.xlsx`;
      }

      // Trigger download
      const response = await fetch(`http://127.0.0.1:8000${downloadUrl}`);
      if (!response.ok) {
        throw new Error("Failed to generate report");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setDialogOpen(false);
      setSelectedAssetId("");
    } catch (error) {
      console.error("Report generation failed:", error);
      alert("Failed to generate report. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const rows = reports.filter((r) => category === "All" || r.category === category);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Reports"
          title="Infrastructure Reports"
          description="Generated risk, condition, analytics and inspection reporting."
          actions={
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button>Generate Report</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Generate Report</DialogTitle>
                  <DialogDescription>
                    Select an asset and report format to generate a downloadable report.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="asset-select">Asset</Label>
                    <Select value={selectedAssetId} onValueChange={setSelectedAssetId}>
                      <SelectTrigger id="asset-select">
                        <SelectValue placeholder="Select an asset..." />
                      </SelectTrigger>
                      <SelectContent>
                        {assets.map((asset) => (
                          <SelectItem key={asset.asset_id} value={asset.asset_id}>
                            {asset.asset_id} - {asset.asset_type} ({asset.city})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="report-type">Report Type</Label>
                    <Select value={selectedReportType} onValueChange={setSelectedReportType}>
                      <SelectTrigger id="report-type">
                        <SelectValue placeholder="Select format..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pdf">PDF Report (Single Asset)</SelectItem>
                        <SelectItem value="csv">CSV Export (All Assets)</SelectItem>
                        <SelectItem value="xlsx">Excel Summary (All Data)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex justify-end gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => setDialogOpen(false)}
                      disabled={isGenerating}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleGenerateReport}
                      disabled={isGenerating || !selectedAssetId}
                    >
                      {isGenerating ? "Generating..." : "Generate"}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          }
        />

        <nav aria-label="Report categories" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <ul className="flex min-w-max gap-2">
            {categories.map((c) => (
              <li key={c}>
                <button
                  type="button"
                  onClick={() => setCategory(c)}
                  className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                    category === c ? "border-primary bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {c}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {rows.length === 0 ? (
          <EmptyState title="No reports in this category" />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {rows.map((r) => (
              <article key={r.id} className="flex h-full flex-col rounded-lg border bg-card p-5 shadow-panel">
                <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/20 bg-primary/8 text-primary">
                    <FileText className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold">{r.title}</h2>
                    <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{r.id}</p>
                  </div>
                </div>

                <p className="mt-4 text-sm text-muted-foreground">{r.summary}</p>

                <dl className="mt-5 grid grid-cols-3 gap-3 border-t pt-4 text-xs">
                  <div>
                    <dt className="eyebrow text-muted-foreground">Type</dt>
                    <dd className="mt-1">{r.type}</dd>
                  </div>
                  <div>
                    <dt className="eyebrow text-muted-foreground">Generated</dt>
                    <dd className="mt-1">{r.generated}</dd>
                  </div>
                  <div>
                    <dt className="eyebrow text-muted-foreground">Status</dt>
                    <dd className={`mt-1 font-medium ${statusTone[r.status] || 'text-muted-foreground'}`}>{r.status}</dd>
                  </div>
                </dl>

                <div className="mt-5 flex gap-2">
                  <Button asChild size="sm" className="flex-1">
                    <Link to="/reports/$id" params={{ id: r.id }}>
                      View
                    </Link>
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1">
                    <Download className="size-4" />
                    Download
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export function ReportDetailsPage({ id }: { id: string }) {
  const [report, setReport] = useState<{ id: string; title: string; category: string; type: string; generated: string; status: string; summary: string; pages: number } | null>(null);

  useEffect(() => {
    apiRequest<{ recent_assessments?: Array<any>; top_high_risk_assets?: Array<any> }>('/api/v1/dashboard/overview')
      .then((payload) => {
        const source = payload.recent_assessments?.length
          ? payload.recent_assessments
          : (payload.top_high_risk_assets ?? []);
        const found = source.find((item) => String(item.assessment_id || item.id) === String(id));
        if (!found) return;
        setReport({
          id: String(found.assessment_id || found.id),
          title: found.assessment_name || found.name || 'Assessment report',
          category: found.risk_level ? 'Risk' : 'Infrastructure',
          type: found.risk_level || 'Portfolio assessment',
          generated: found.last_assessed || 'Live',
          status: 'Ready',
          summary: `${found.assessment_name || found.name || 'Asset'} shows a ${Number(found.risk_score ?? 0).toFixed(1)} risk score and ${Number(found.health_score ?? 0).toFixed(0)} health score.`,
          pages: 8,
        });
      })
      .catch((error) => console.error('Report detail fetch failed', error));
  }, [id]);

  if (!report) {
    return (
      <DashboardLayout>
        <EmptyState title="Report not found" description={`No report matches the identifier ${id}.`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/reports" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to Reports
        </Link>

        <PageHeader
          eyebrow={`${report.id} · ${report.category}`}
          title={report.title}
          description={`${report.type} · Generated ${report.generated} · ${report.pages} pages`}
          actions={
            <Button variant="outline">
              <Download className="size-4" />
              Download
            </Button>
          }
        />

        <ChartCard title="Report Viewer" subtitle={`Status: ${report.status}`}>
          <div className="rounded-md border bg-surface p-6">
            <p className="text-sm leading-relaxed">{report.summary}</p>
            <div className="mt-6 space-y-4">
              {["Scope and methodology", "Condition assessment", "Risk findings", "Recommended actions"].map((section, i) => (
                <div key={section} className="border-t pt-4 first:border-0 first:pt-0">
                  <p className="font-mono text-xs text-primary">{String(i + 1).padStart(2, "0")}</p>
                  <h3 className="mt-1.5 text-sm font-semibold">{section}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    Generated from the active database for this asset assessment.
                  </p>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>
    </DashboardLayout>
  );
}
