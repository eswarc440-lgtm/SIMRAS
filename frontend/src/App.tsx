import BridgeEngineeringViewer from "./features/digital-twin/BridgeEngineeringViewer";
import RealityTwinAssetViewer from "./features/digital-twin/RealityTwinAssetViewer";
import { useEffect, useMemo, useState } from "react";
import { AssetList } from "./components/AssetList";
import { GISMap } from "./components/GISMap";
import { KpiCard } from "./components/KpiCard";
import { StatusPill } from "./components/StatusPill";
import { TwinPanels } from "./features/digital-twin/TwinPanels";
import { SelectedAssetReports } from "./features/reports/SelectedAssetReports";
import { api } from "./services/api";
import type { EvidenceStateResponse } from "./types/evidence";
import LegacyOverlayPruner from "./features/digital-twin/LegacyOverlayPruner";
import DigitalTwinTelemetryPruner from "./features/digital-twin/DigitalTwinTelemetryPruner";
import type {
  AssetSummary,
  MapFeatureCollection,
  MapFeatureSummaryItem,
  TwinResponse,
} from "./types/twin";

type Workspace = "GIS" | "TWIN" | "REPORTS";
type ViewerMode = "ASSET_MODEL" | "GEOSPATIAL";

const emptyMapFeatures: MapFeatureCollection = {
  type: "FeatureCollection",
  features: [],
  total: 0,
  limit: 5000,
  offset: 0,
};

export default function App() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [selected, setSelected] = useState<AssetSummary>();
  const [twin, setTwin] = useState<TwinResponse>();
  const [evidenceState, setEvidenceState] =
    useState<EvidenceStateResponse>();
  const [workspace, setWorkspace] = useState<Workspace>("GIS");
  const [viewerMode, setViewerMode] =
    useState<ViewerMode>("ASSET_MODEL");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [mapFeatureType, setMapFeatureType] = useState("airport");
  const [mapFeatures, setMapFeatures] =
    useState<MapFeatureCollection>(emptyMapFeatures);
  const [mapSummary, setMapSummary] =
    useState<MapFeatureSummaryItem[]>([]);
  const [mapLoading, setMapLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(undefined);

    api.assets({
      assetType:
        typeFilter === "all"
          ? undefined
          : typeFilter,
      search:
        query.trim() || undefined,
      limit: 1000,
      offset: 0,
    })
      .then((response) => {
        if (cancelled) return;

        const ranked = [...response.items].sort(
          (a, b) =>
            (b.risk_score ?? -1) -
            (a.risk_score ?? -1),
        );

        setAssets(ranked);

        const defaultCode =
          import.meta.env.VITE_DEFAULT_ASSET_ID;

        setSelected((current) => {
          if (current) {
            const sameAsset = ranked.find(
              (asset) =>
                asset.asset_code ===
                current.asset_code,
            );

            if (sameAsset) {
              return sameAsset;
            }
          }

          return (
            ranked.find(
              (asset) =>
                asset.asset_code ===
                defaultCode,
            ) ??
            ranked[0]
          );
        });
      })
      .catch((cause: unknown) => {
        if (cancelled) return;

        setError(
          cause instanceof Error
            ? cause.message
            : String(cause),
        );
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [typeFilter, query]);

  useEffect(() => {
    api.mapSummary()
      .then((response) =>
        setMapSummary(response.items),
      )
      .catch((cause: unknown) =>
        setError(
          cause instanceof Error
            ? cause.message
            : String(cause),
        ),
      );
  }, []);

  useEffect(() => {
    setMapLoading(true);

    api.mapFeatures(
      mapFeatureType === "all" ? undefined : mapFeatureType,
    )
      .then(setMapFeatures)
      .catch((cause: unknown) =>
        setError(
          cause instanceof Error ? cause.message : String(cause),
        ),
      )
      .finally(() => setMapLoading(false));
  }, [mapFeatureType]);

  useEffect(() => {
    if (!selected) return;

    let cancelled = false;
    const assetCode = selected.asset_code;

    setTwin(undefined);
    setEvidenceState(undefined);
    setError(undefined);

    Promise.allSettled([
      api.twin(assetCode),
      api.state(assetCode),
    ]).then(([twinResult, stateResult]) => {
      if (cancelled) return;

      if (twinResult.status === "fulfilled") {
        if (twinResult.value.asset.asset_code === assetCode) {
          setTwin(twinResult.value);
        }
      } else {
        setError(
          twinResult.reason instanceof Error
            ? twinResult.reason.message
            : String(twinResult.reason),
        );
      }

      if (stateResult.status === "fulfilled") {
        setEvidenceState(stateResult.value);
      } else {
        setError(
          stateResult.reason instanceof Error
            ? stateResult.reason.message
            : String(stateResult.reason),
        );
      }
    });

    return () => {
      cancelled = true;
    };
  }, [selected]);

  const filteredAssets = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    return assets.filter((asset) => {
      const matchesType =
        typeFilter === "all" || asset.asset_type === typeFilter;

      const matchesText =
        !normalized ||
        `${asset.name} ${asset.district ?? ""}`
          .toLowerCase()
          .includes(normalized);

      return matchesType && matchesText;
    });
  }, [assets, query, typeFilter]);

  const mapLayers = useMemo(() => {
    const totals = new Map<string, number>();

    for (const item of mapSummary) {
      totals.set(
        item.feature_type,
        (totals.get(item.feature_type) ?? 0) + item.records,
      );
    }

    return [...totals.entries()]
      .map(([featureType, records]) => ({
        featureType,
        records,
      }))
      .sort((a, b) =>
        a.featureType.localeCompare(b.featureType),
      );
  }, [mapSummary]);

  const mapFeatureTotal = mapLayers.reduce(
    (total, layer) => total + layer.records,
    0,
  );

  const highRisk = assets.filter(
    (asset) => asset.risk_level === "HIGH",
  ).length;

  const verified = assets.filter(
    (asset) => asset.identity_status === "VERIFIED",
  ).length;

  return (
    <div className="app-shell">
      <DigitalTwinTelemetryPruner />
      <LegacyOverlayPruner />
      <header className="topbar">
        <div className="brand-mark">S</div>
        <div className="brand-copy">
          <strong>SIMRAS</strong>
          <span>Infrastructure intelligence · Andhra Pradesh</span>
        </div>

        <nav>
          <button
            className={workspace === "GIS" ? "active" : ""}
            onClick={() => setWorkspace("GIS")}
          >
            GIS command
          </button>

          <button
            className={workspace === "TWIN" ? "active" : ""}
            onClick={() => setWorkspace("TWIN")}
          >
            Digital twin
          </button>
          <button
            className={workspace === "REPORTS" ? "active" : ""}
            onClick={() => setWorkspace("REPORTS")}
          >
            Reports
          </button>
        </nav>

        <StatusPill label="Evidence backed" tone="good" />
      </header>

      <main>
        <section className="hero-row">
          <div>
            <span className="eyebrow">
              AP DAMS · BRIDGES · BARRAGES · AIRPORTS · TEMPLES
            </span>

            <h1>
              {workspace === "GIS"
                ? "Infrastructure risk command"
                : workspace === "REPORTS"
                  ? "Selected asset reports"
                  : selected?.name ?? "Digital twin"}
            </h1>

            <p>
              Government observations, official evidence, source,
              timestamp, quality and confidence are shown separately.
              Missing structural evidence remains UNKNOWN.
            </p>
          </div>

          {selected && (
            <button
              className="primary-action"
              onClick={() => setWorkspace("TWIN")}
            >
              Open selected twin →
            </button>
          )}
        </section>

        {error && (
          <div className="error-banner">
            <strong>Connection problem</strong>
            <span>{error}</span>
          </div>
        )}

        <section className="kpi-grid">
          <KpiCard
            label="Registry"
            value={assets.length}
            detail="Canonical monitored assets"
          />

          <KpiCard
            label="Map features"
            value={mapFeatureTotal}
            detail="Source-reported GIS context"
            accent="#38bdf8"
          />

          <KpiCard
            label="High risk"
            value={highRisk}
            detail="Existing registry classification"
            accent="#ff5b62"
          />

          <KpiCard
            label="Verified identity"
            value={verified}
            detail="Authoritatively cross-checked"
            accent="#37d3a2"
          />
        </section>

        {workspace === "GIS" ? (
          <section className="workspace-grid">
            <aside className="asset-sidebar">
              <div className="filters">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search asset or district"
                />

                <select
                  value={typeFilter}
                  onChange={(event) => setTypeFilter(event.target.value)}
                >
                  <option value="all">All assets</option>
                  <option value="dam">Dams</option>
                  <option value="bridge">Bridges</option>
                  <option value="barrage">Barrages</option>
                  <option value="airport">Airports</option>
                  <option value="temple">Temples</option>
                </select>
              </div>

              {loading ? (
                <p className="loading">Loading registry…</p>
              ) : (
                <AssetList
                  assets={filteredAssets}
                  selectedCode={selected?.asset_code}
                  onSelect={setSelected}
                />
              )}
            </aside>

            <div className="map-stage">
              <GISMap
                assets={filteredAssets}
                mapFeatures={emptyMapFeatures}
                selected={selected}
                onSelect={setSelected}
              />

              <div className="map-legend">
                <span><i className="low" />Low</span>
                <span><i className="medium" />Medium</span>
                <span><i className="high" />High</span>
              </div>
            </div>
          </section>
        ) : workspace === "REPORTS" ? (
          <SelectedAssetReports selected={selected} twin={twin} />
        ) : (
          <section className="twin-workspace">
            <div className="twin-header">
              <div>
                <span className="asset-code">
                  {selected?.asset_code}
                </span>

                <StatusPill
                  label={selected?.identity_status ?? "UNKNOWN"}
                  tone={
                    selected?.identity_status === "VERIFIED"
                      ? "good"
                      : "warn"
                  }
                />
              </div>

              <div className="segmented-control" style={{ display: "none" }}>
                <button
                  className={
                    viewerMode === "ASSET_MODEL"
                      ? "active"
                      : ""
                  }
                  onClick={() => setViewerMode("ASSET_MODEL")}
                >
                  Asset model
                </button>

                <button
                  className={
                    viewerMode === "GEOSPATIAL"
                      ? "active"
                      : ""
                  }
                  onClick={() => setViewerMode("GEOSPATIAL")}
                >
                  Terrain & buildings 3D
                </button>
              </div>
            </div>

            {twin ? (
              <>
                <div className="twin-stage">
                  {selected?.asset_code?.startsWith("AP_BR_") ? (
                    <BridgeEngineeringViewer
                      assetCode={selected.asset_code}
                    />
                  ) : (
                    <RealityTwinAssetViewer
                      assetCode={selected?.asset_code}
                    />
                  )}
                </div>

                {!evidenceState && (
                  <p className="loading">
                    Loading government evidence state...
                  </p>
                )}

              </>
            ) : (
              <p className="loading">
                Building canonical twin state…
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
