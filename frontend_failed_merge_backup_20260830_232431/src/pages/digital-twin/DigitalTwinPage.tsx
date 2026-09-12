import { useEffect, useMemo, useState } from "react";
import { Box, Map, Search } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Input } from "../../components/ui/input";
import { api as twinApi } from "../../services/simrasTwinApi";
import { TwinViewer3D } from "../../features/digital-twin/TwinViewer3D";
import { CesiumTwinViewer } from "../../features/digital-twin/CesiumTwinViewer";
import { GoogleMapStreetView } from "../../features/digital-twin/GoogleMapStreetView";
import { TwinPanels } from "../../features/digital-twin/TwinPanels";
import { EvidenceStatePanel } from "../../features/digital-twin/EvidenceStatePanel";
import type { TwinResponse } from "../../types/twin";
import type { EvidenceStateResponse } from "../../types/evidence";

type Mode = "ASSET_MODEL" | "MAP_2D" | "GEOSPATIAL";

export function DigitalTwinPage() {
  const [assets, setAssets] = useState<any[]>([]);
  const [selectedCode, setSelectedCode] = useState<string>();
  const [twin, setTwin] = useState<TwinResponse>();
  const [evidence, setEvidence] = useState<EvidenceStateResponse>();
  const [mode, setMode] = useState<Mode>("ASSET_MODEL");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    twinApi.assets().then((r) => {
      setAssets(r.items ?? []);
      if (r.items?.length) setSelectedCode(r.items[0].asset_code);
    }).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedCode) return;
    setError(undefined);
    Promise.allSettled([twinApi.twin(selectedCode), twinApi.state(selectedCode)]).then(([t, s]) => {
      if (t.status === "fulfilled") setTwin(t.value); else setError(String(t.reason));
      if (s.status === "fulfilled") setEvidence(s.value); else setEvidence(undefined);
    });
  }, [selectedCode]);

  const filtered = useMemo(() => assets.filter((a) =>
    `${a.asset_code} ${a.name} ${a.asset_type} ${a.district}`.toLowerCase().includes(query.toLowerCase())
  ), [assets, query]);

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow text-muted-foreground">REAL ASSET WORKSPACE</p>
            <h1 className="text-2xl font-bold">Infrastructure Digital Twin</h1>
          </div>
          <div className="inline-flex rounded-md border p-0.5">
            {([
              ["ASSET_MODEL", "Asset model"],
              ["MAP_2D", "2D map"],
              ["GEOSPATIAL", "Terrain & buildings 3D"],
            ] as const).map(([value, label]) => (
              <button key={value} onClick={() => setMode(value)} className={`rounded px-3 py-2 text-xs font-medium ${mode === value ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>{label}</button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="rounded-lg border bg-card p-3">
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search asset..." className="pl-9" />
            </div>
            <div className="max-h-[66vh] space-y-1 overflow-auto">
              {filtered.map((asset) => (
                <button key={asset.asset_code} onClick={() => setSelectedCode(asset.asset_code)} className={`w-full rounded-md border p-3 text-left text-sm ${selectedCode === asset.asset_code ? "border-primary bg-primary/10" : "border-transparent hover:bg-muted"}`}>
                  <div className="font-mono text-[11px] text-muted-foreground">{asset.asset_code}</div>
                  <div className="font-semibold">{asset.name}</div>
                  <div className="text-xs text-muted-foreground">{asset.asset_type} Â· {asset.district}</div>
                </button>
              ))}
            </div>
          </aside>

          <main className="min-w-0 space-y-4">
            <section className="overflow-hidden rounded-lg border bg-card">
              {loading ? <div className="grid h-[620px] place-items-center">Loading assetsâ€¦</div> : error ? <div className="grid h-[620px] place-items-center p-6 text-danger">{error}</div> : !twin ? <div className="grid h-[620px] place-items-center">Select an asset.</div> : (
                <div className="h-[620px]">
                  {mode === "ASSET_MODEL" && <TwinViewer3D twin={twin} />}
                  {mode === "MAP_2D" && <GoogleMapStreetView twin={twin} />}
                  {mode === "GEOSPATIAL" && <CesiumTwinViewer twin={twin} />}
                </div>
              )}
            </section>
            {twin && <TwinPanels twin={twin} />}
            {evidence && <EvidenceStatePanel state={evidence} />}
          </main>
        </div>
      </div>
    </DashboardLayout>
  );
}
