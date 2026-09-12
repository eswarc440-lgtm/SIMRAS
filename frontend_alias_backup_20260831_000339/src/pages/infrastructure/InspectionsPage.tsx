import { useEffect, useState } from "react";
import { Plus, Search, MapPin, Calendar, User, AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { apiRequest } from "../../services/api";

interface Inspection {
  id: string | number;
  asset_id: string;
  inspection_type?: string;
  inspection_date: string;
  inspector?: string;
  inspection_score?: number;
  condition?: string;
  notes?: string;
  severity?: string;
  crack_severity?: string;
  corrosion_level?: string;
  structural_defect_level?: string;
  inspection_status?: string;
  created_at: string;
  // Legacy fields support
  inspector_name?: string;
  condition_score?: number;
  remarks?: string;
}

export function InspectionsPage() {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedInspection, setSelectedInspection] = useState<Inspection | null>(null);

  useEffect(() => {
    const loadInspections = async () => {
      try {
        setLoading(true);
        const response = await apiRequest<{ 
          total: number; 
          limit?: number; 
          skip?: number;
          items?: Inspection[];
          inspections?: Inspection[];
        }>("/api/v1/inspections?limit=100");
        
        // Support both 'items' and 'inspections' keys from backend
        const data = response.items || response.inspections || [];
        setInspections(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error("Failed to load inspections", error);
        setInspections([]);
      } finally {
        setLoading(false);
      }
    };

    void loadInspections();
  }, []);

  const filtered = inspections.filter(
    (i) =>
      i.asset_id.toLowerCase().includes(search.toLowerCase()) ||
      (i.inspection_type || "").toLowerCase().includes(search.toLowerCase()) ||
      (i.inspector || i.inspector_name || "").toLowerCase().includes(search.toLowerCase())
  );

  const getConditionBadge = (score: number | null | undefined) => {
    if (score === null || score === undefined) return null;
    if (score >= 80) return <span className="rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800">Good</span>;
    if (score >= 60) return <span className="rounded bg-yellow-100 px-2 py-1 text-xs font-semibold text-yellow-800">Fair</span>;
    return <span className="rounded bg-red-100 px-2 py-1 text-xs font-semibold text-red-800">Poor</span>;
  };

  const getConditionScore = (inspection: Inspection): number | undefined => {
    return inspection.condition_score ?? inspection.inspection_score;
  };

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Inspections</h1>
            <p className="text-sm text-muted-foreground">View and manage asset inspections</p>
          </div>
          <Button>
            <Plus className="mr-2 size-4" />
            New Inspection
          </Button>
        </div>

        <div className="rounded-lg border bg-card p-6">
          <div className="mb-6 flex gap-3">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by asset, type, or inspector..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {loading ? (
            <div className="py-12 text-center text-muted-foreground">Loading inspections...</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">No inspections found</div>
          ) : (
            <div className="space-y-3">
              {filtered.map((inspection) => (
                <div
                  key={inspection.id}
                  onClick={() => setSelectedInspection(inspection)}
                  className="cursor-pointer rounded-lg border border-border bg-background p-4 transition-colors hover:bg-muted"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-mono text-sm font-semibold">{inspection.asset_id}</p>
                        {inspection.inspection_type && (
                          <span className="rounded bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                            {inspection.inspection_type}
                          </span>
                        )}
                        {getConditionScore(inspection) && getConditionBadge(getConditionScore(inspection))}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Calendar className="size-3.5" />
                          {new Date(inspection.inspection_date).toLocaleDateString()}
                        </div>
                        {(inspection.inspector || inspection.inspector_name) && (
                          <div className="flex items-center gap-1">
                            <User className="size-3.5" />
                            {inspection.inspector || inspection.inspector_name}
                          </div>
                        )}
                        {getConditionScore(inspection) !== null && getConditionScore(inspection) !== undefined && (
                          <div className="flex items-center gap-1">
                            <AlertCircle className="size-3.5" />
                            Score: {getConditionScore(inspection)?.toFixed(1)}/100
                          </div>
                        )}
                      </div>
                      {(inspection.remarks || inspection.notes) && (
                        <p className="mt-2 text-sm">{(inspection.remarks || inspection.notes)?.substring(0, 100)}...</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedInspection && (
          <div className="rounded-lg border bg-card p-6">
            <h2 className="mb-4 text-xl font-semibold">Inspection Details</h2>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="font-semibold text-muted-foreground">Asset ID</dt>
                <dd className="mt-1">{selectedInspection.asset_id}</dd>
              </div>
              <div>
                <dt className="font-semibold text-muted-foreground">Type</dt>
                <dd className="mt-1">{selectedInspection.inspection_type || "N/A"}</dd>
              </div>
              <div>
                <dt className="font-semibold text-muted-foreground">Date</dt>
                <dd className="mt-1">{new Date(selectedInspection.inspection_date).toLocaleString()}</dd>
              </div>
              <div>
                <dt className="font-semibold text-muted-foreground">Inspector</dt>
                <dd className="mt-1">{selectedInspection.inspector || selectedInspection.inspector_name || "N/A"}</dd>
              </div>
              {getConditionScore(selectedInspection) !== null && getConditionScore(selectedInspection) !== undefined && (
                <div>
                  <dt className="font-semibold text-muted-foreground">Condition Score</dt>
                  <dd className="mt-1">{getConditionScore(selectedInspection)?.toFixed(1)}/100</dd>
                </div>
              )}
              {selectedInspection.severity && (
                <div>
                  <dt className="font-semibold text-muted-foreground">Severity</dt>
                  <dd className="mt-1">{selectedInspection.severity}</dd>
                </div>
              )}
              <div>
                <dt className="font-semibold text-muted-foreground">Created</dt>
                <dd className="mt-1">{new Date(selectedInspection.created_at).toLocaleDateString()}</dd>
              </div>
            </dl>
            {(selectedInspection.remarks || selectedInspection.notes) && (
              <div className="mt-4">
                <dt className="font-semibold text-muted-foreground">Notes</dt>
                <dd className="mt-1">{selectedInspection.remarks || selectedInspection.notes}</dd>
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
