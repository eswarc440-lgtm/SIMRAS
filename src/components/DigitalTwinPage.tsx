import { Box, Database, MapPin } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import RealityTwinAssetViewer from "../features/digital-twin/RealityTwinAssetViewer";
import type { AssetSummary } from "../types/twin";
import { TwinAssessmentPanel } from "./twin/TwinAssessmentPanel";
import { TwinEvidenceTables } from "./twin/TwinEvidenceTables";
import { buildTwinViewModel } from "./twin/twinViewModel";

interface DigitalTwinPageProps {
  assets: AssetSummary[];
  selectedAsset: AssetSummary;
  onSelectAsset: (asset: AssetSummary) => void;
  onNavigateToReports: (assetCode: string) => void;
}

interface TwinPageData {
  twin: Record<string, any>;
  assessment: Record<string, any>;
  telemetry: Record<string, any> | null;
  inspections: Record<string, any>[];
  maintenance: Record<string, any>[];
}

const emptyData: TwinPageData = {
  twin: {},
  assessment: {},
  telemetry: null,
  inspections: [],
  maintenance: [],
};

async function jsonOr<T>(url: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(url);
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}

export function DigitalTwinPage({
  assets,
  selectedAsset,
  onSelectAsset,
  onNavigateToReports,
}: DigitalTwinPageProps) {
  const [data, setData] = useState<TwinPageData>(emptyData);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const code = encodeURIComponent(selectedAsset.asset_code);
    setLoading(true);
    setData(emptyData);

    Promise.all([
      jsonOr(`/api/v1/assets/${code}/twin`, {}),
      jsonOr(`/api/v1/assets/${code}/assessment`, {}),
      jsonOr<Record<string, any> | null>(`/api/v1/assets/${code}/telemetry`, null),
      jsonOr<Record<string, any>[]>(`/api/v1/inspections?asset_code=${code}`, []),
      jsonOr<Record<string, any>[]>(`/api/v1/maintenance?asset_code=${code}`, []),
    ]).then(([twin, assessment, telemetry, inspections, maintenance]) => {
      if (!active) return;
      setData({ twin, assessment, telemetry, inspections, maintenance });
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [selectedAsset.asset_code]);

  const view = useMemo(
    () =>
      buildTwinViewModel(
        selectedAsset,
        data.twin,
        data.assessment,
        data.telemetry,
        data.inspections,
        data.maintenance,
      ),
    [data, selectedAsset],
  );

  const source =
    data.twin?.source_profile?.authority ??
    data.twin?.twin?.model_source ??
    "NOT VERIFIED";
  const fidelity = data.twin?.twin?.fidelity_level ?? "PROXY";

  return (
    <div className="min-h-screen bg-[#F5F7FA] text-slate-800">
      <header className="border-b border-[#DDE5EC] bg-white px-4 py-3 sm:px-6">
        <div className="flex flex-col justify-between gap-3 xl:flex-row xl:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-wide">
              <span className="rounded border border-blue-200 bg-blue-50 px-2 py-1 font-mono text-[#0875BE]">{selectedAsset.asset_code}</span>
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-slate-600">{selectedAsset.identity_status || "NOT VERIFIED"}</span>
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-slate-600">Twin {fidelity}</span>
            </div>
            <h1 className="mt-1 text-xl font-extrabold text-[#0C4775] sm:text-2xl">{selectedAsset.name}</h1>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{selectedAsset.district || "District not available"}</span>
              <span>•</span>
              <span>{selectedAsset.category || selectedAsset.type || selectedAsset.asset_type}</span>
            </p>
          </div>

          <label className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
            Active infrastructure
            <select
              value={selectedAsset.asset_code}
              onChange={(event) => {
                const asset = assets.find((item) => item.asset_code === event.target.value);
                if (asset) onSelectAsset(asset);
              }}
              className="mt-1 block min-w-64 rounded-md border border-[#DDE5EC] bg-white px-3 py-2 text-xs font-semibold normal-case text-slate-800"
            >
              {assets.map((asset) => <option key={asset.asset_code} value={asset.asset_code}>{asset.name} ({asset.asset_code})</option>)}
            </select>
          </label>
        </div>
      </header>

      <main className="space-y-5 p-4 sm:p-5">
        <section className="grid min-h-[620px] gap-4 lg:h-[calc(100vh-10.5rem)] lg:min-h-[640px] lg:grid-cols-[minmax(0,3fr)_minmax(290px,1fr)]">
          <div className="flex min-h-[520px] flex-col overflow-hidden rounded-xl border border-[#DDE5EC] bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-[#DDE5EC] px-4 py-3">
              <h2 className="flex items-center gap-2 text-sm font-bold text-[#0C4775]"><Box className="h-4 w-4 text-[#0875BE]" />Digital Twin</h2>
              <span className="text-[10px] font-bold uppercase text-slate-400">{loading ? "Loading model context" : "Asset-specific viewer"}</span>
            </div>
            <div className="min-h-0 flex-1 bg-slate-950">
              <RealityTwinAssetViewer assetCode={selectedAsset.asset_code} />
            </div>
          </div>

          <TwinAssessmentPanel
            asset={selectedAsset}
            view={view}
            loading={loading}
            onOpenReport={() => onNavigateToReports(selectedAsset.asset_code)}
          />
        </section>

        <section className="grid gap-3 rounded-xl border border-[#DDE5EC] bg-white p-4 text-xs shadow-sm md:grid-cols-3">
          <div><span className="block text-[10px] font-bold uppercase text-slate-400">Data source</span><strong className="mt-1 block text-slate-700">{source}</strong></div>
          <div><span className="block text-[10px] font-bold uppercase text-slate-400">Telemetry state</span><strong className="mt-1 block text-slate-700">{view.telemetryState}</strong></div>
          <div className="flex items-center gap-2"><Database className="h-4 w-4 text-[#0875BE]" /><span><span className="block text-[10px] font-bold uppercase text-slate-400">Evidence policy</span><strong className="mt-1 block text-slate-700">No synthetic fallback values</strong></span></div>
        </section>

        <TwinEvidenceTables view={view} />
      </main>
    </div>
  );
}
