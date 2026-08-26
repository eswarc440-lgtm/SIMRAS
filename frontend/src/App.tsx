import { useEffect, useMemo, useState } from "react";
import { AssetList } from "./components/AssetList";
import { GISMap } from "./components/GISMap";
import { KpiCard } from "./components/KpiCard";
import { StatusPill } from "./components/StatusPill";
import { CesiumTwinViewer } from "./features/digital-twin/CesiumTwinViewer";
import { TwinPanels } from "./features/digital-twin/TwinPanels";
import { TwinViewer3D } from "./features/digital-twin/TwinViewer3D";
import { api } from "./services/api";
import type { AssetSummary, TwinResponse } from "./types/twin";

type Workspace = "GIS" | "TWIN";
type ViewerMode = "CLOSE_UP" | "GEOSPATIAL";

export default function App() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [selected, setSelected] = useState<AssetSummary>();
  const [twin, setTwin] = useState<TwinResponse>();
  const [workspace, setWorkspace] = useState<Workspace>("GIS");
  const [viewerMode, setViewerMode] = useState<ViewerMode>("CLOSE_UP");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.assets()
      .then((response) => {
        const ranked = [...response.items].sort((a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1));
        setAssets(ranked);
        const defaultCode = import.meta.env.VITE_DEFAULT_ASSET_ID;
        setSelected(ranked.find((asset) => asset.asset_code === defaultCode) ?? ranked[0]);
      })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setTwin(undefined);
    api.twin(selected.asset_code)
      .then(setTwin)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)));
  }, [selected]);

  const filteredAssets = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return assets.filter((asset) => {
      const matchesType = typeFilter === "all" || asset.asset_type === typeFilter;
      const matchesText = !normalized || `${asset.name} ${asset.district ?? ""}`.toLowerCase().includes(normalized);
      return matchesType && matchesText;
    });
  }, [assets, query, typeFilter]);

  const highRisk = assets.filter((asset) => asset.risk_level === "HIGH").length;
  const verified = assets.filter((asset) => asset.identity_status === "VERIFIED").length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">S</div>
        <div className="brand-copy">
          <strong>SIMRAS</strong>
          <span>Infrastructure intelligence · Andhra Pradesh</span>
        </div>
        <nav>
          <button className={workspace === "GIS" ? "active" : ""} onClick={() => setWorkspace("GIS")}>GIS command</button>
          <button className={workspace === "TWIN" ? "active" : ""} onClick={() => setWorkspace("TWIN")}>Digital twin</button>
        </nav>
        <StatusPill label="Decision support" tone="warn" />
      </header>

      <main>
        <section className="hero-row">
          <div>
            <span className="eyebrow">AP BRIDGES · DAMS · BARRAGES</span>
            <h1>{workspace === "GIS" ? "Infrastructure risk command" : selected?.name ?? "Digital twin"}</h1>
            <p>
              Every value carries its source, timestamp, quality and confidence. Unverified seed data is never presented as engineering truth.
            </p>
          </div>
          {selected && (
            <button className="primary-action" onClick={() => setWorkspace("TWIN")}>Open selected twin →</button>
          )}
        </section>

        {error && <div className="error-banner"><strong>Connection problem</strong><span>{error}</span></div>}

        <section className="kpi-grid">
          <KpiCard label="Registry" value={assets.length} detail="Bootstrapped assets" />
          <KpiCard label="High risk" value={highRisk} detail="Decision-support classification" accent="#ff5b62" />
          <KpiCard label="Verified identity" value={verified} detail="Requires authoritative cross-check" accent="#37d3a2" />
          <KpiCard label="Sensors" value="0" detail="No physical feeds connected" accent="#f3b647" />
        </section>

        {workspace === "GIS" ? (
          <section className="workspace-grid">
            <aside className="asset-sidebar">
              <div className="filters">
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search asset or district" />
                <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                  <option value="all">All types</option>
                  <option value="bridge">Bridges</option>
                  <option value="dam">Dams</option>
                  <option value="barrage">Barrages</option>
                </select>
              </div>
              {loading ? <p className="loading">Loading registry…</p> : (
                <AssetList assets={filteredAssets} selectedCode={selected?.asset_code} onSelect={setSelected} />
              )}
            </aside>
            <div className="map-stage">
              <GISMap assets={filteredAssets} selected={selected} onSelect={setSelected} />
              <div className="map-legend">
                <span><i className="low" />Low</span><span><i className="medium" />Medium</span><span><i className="high" />High</span>
              </div>
            </div>
          </section>
        ) : (
          <section className="twin-workspace">
            <div className="twin-header">
              <div>
                <span className="asset-code">{selected?.asset_code}</span>
                <StatusPill label={selected?.identity_status ?? "UNKNOWN"} tone={selected?.identity_status === "VERIFIED" ? "good" : "warn"} />
              </div>
              <div className="segmented-control">
                <button className={viewerMode === "CLOSE_UP" ? "active" : ""} onClick={() => setViewerMode("CLOSE_UP")}>Close-up 3D</button>
                <button className={viewerMode === "GEOSPATIAL" ? "active" : ""} onClick={() => setViewerMode("GEOSPATIAL")}>Geospatial 3D</button>
              </div>
            </div>
            {twin ? (
              <>
                <div className="twin-stage">
                  {viewerMode === "CLOSE_UP" ? <TwinViewer3D twin={twin} /> : <CesiumTwinViewer twin={twin} />}
                </div>
                <TwinPanels twin={twin} />
              </>
            ) : <p className="loading">Building canonical twin state…</p>}
          </section>
        )}
      </main>
    </div>
  );
}

