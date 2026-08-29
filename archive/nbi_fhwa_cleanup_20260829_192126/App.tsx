import { useEffect, useMemo, useState } from "react";

import { AssetList } from "./components/AssetList";
import { GISMap } from "./components/GISMap";
import { KpiCard } from "./components/KpiCard";
import { StatusPill } from "./components/StatusPill";

import { CesiumTwinViewer } from "./features/digital-twin/CesiumTwinViewer";
import { TwinPanels } from "./features/digital-twin/TwinPanels";
import { TwinViewer3D } from "./features/digital-twin/TwinViewer3D";

import { api } from "./services/api";

import type {
  AssetSummary,
  MapFeatureCollection,
  MapFeatureSummaryItem,
  TwinResponse,
} from "./types/twin";

type Workspace = "GIS" | "TWIN";
type ViewerMode = "ASSET_MODEL" | "GEOSPATIAL";

const emptyMapFeatures: MapFeatureCollection = {
  type: "FeatureCollection",
  features: [],
  total: 0,
  limit: 5000,
  offset: 0,
};

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

export default function App() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [selected, setSelected] = useState<AssetSummary>();
  const [twin, setTwin] = useState<TwinResponse>();

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

  const [loadingAssets, setLoadingAssets] = useState(true);
  const [loadingTwin, setLoadingTwin] = useState(false);
  const [mapLoading, setMapLoading] = useState(false);

  const [error, setError] = useState<string>();

  // ============================================================
  // Load canonical assets
  // ============================================================

  useEffect(() => {
    let cancelled = false;

    async function loadAssets() {
      setLoadingAssets(true);

      try {
        const response = await api.assets();

        if (cancelled) {
          return;
        }

        const ranked = [...response.items].sort(
          (a, b) =>
            (b.risk_score ?? -1) - (a.risk_score ?? -1),
        );

        setAssets(ranked);

        const defaultCode =
          import.meta.env.VITE_DEFAULT_ASSET_ID;

        const defaultAsset =
          ranked.find(
            (asset) =>
              asset.asset_code === defaultCode,
          ) ?? ranked[0];

        setSelected(defaultAsset);
      } catch (cause: unknown) {
        if (!cancelled) {
          setError(
            `Asset registry: ${errorMessage(cause)}`,
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingAssets(false);
        }
      }
    }

    void loadAssets();

    return () => {
      cancelled = true;
    };
  }, []);

  // ============================================================
  // Load GIS layer summary
  // ============================================================

  useEffect(() => {
    let cancelled = false;

    async function loadMapSummary() {
      try {
        const response = await api.mapSummary();

        if (!cancelled) {
          setMapSummary(response.items);
        }
      } catch (cause: unknown) {
        if (!cancelled) {
          setError(
            `GIS summary: ${errorMessage(cause)}`,
          );
        }
      }
    }

    void loadMapSummary();

    return () => {
      cancelled = true;
    };
  }, []);

  // ============================================================
  // Load GIS features
  // ============================================================

  useEffect(() => {
    let cancelled = false;

    async function loadMapFeatures() {
      setMapLoading(true);

      try {
        const response = await api.mapFeatures(
          mapFeatureType === "all"
            ? undefined
            : mapFeatureType,
        );

        if (!cancelled) {
          setMapFeatures(response);
        }
      } catch (cause: unknown) {
        if (!cancelled) {
          setError(
            `GIS layer: ${errorMessage(cause)}`,
          );
        }
      } finally {
        if (!cancelled) {
          setMapLoading(false);
        }
      }
    }

    void loadMapFeatures();

    return () => {
      cancelled = true;
    };
  }, [mapFeatureType]);

  // ============================================================
  // Load selected Digital Twin
  // ============================================================

  useEffect(() => {
    if (!selected) {
      setTwin(undefined);
      return;
    }

    const assetCode = selected.asset_code;
    let cancelled = false;

    async function loadTwin() {
      setLoadingTwin(true);
      setTwin(undefined);

      try {
        const response = await api.twin(assetCode);

        if (!cancelled) {
          setTwin(response);
        }
      } catch (cause: unknown) {
        if (!cancelled) {
          setError(
            `Digital twin: ${errorMessage(cause)}`,
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingTwin(false);
        }
      }
    }

    void loadTwin();

    return () => {
      cancelled = true;
    };
  }, [selected]);

  // ============================================================
  // Filter assets
  // ============================================================

  const filteredAssets = useMemo(() => {
    const normalized = query
      .trim()
      .toLowerCase();

    return assets.filter((asset) => {
      const matchesType =
        typeFilter === "all" ||
        asset.asset_type === typeFilter;

      const searchable =
        `${asset.name} ${asset.district ?? ""} ${asset.asset_code}`
          .toLowerCase();

      const matchesText =
        !normalized ||
        searchable.includes(normalized);

      return matchesType && matchesText;
    });
  }, [assets, query, typeFilter]);

  // ============================================================
  // Map layer totals
  // ============================================================

  const mapLayers = useMemo(() => {
    const totals = new Map<string, number>();

    for (const item of mapSummary) {
      totals.set(
        item.feature_type,
        (totals.get(item.feature_type) ?? 0) +
          item.records,
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

  // ============================================================
  // KPI values
  // ============================================================

  const mapFeatureTotal = mapLayers.reduce(
    (total, layer) =>
      total + layer.records,
    0,
  );

  const highRisk = assets.filter(
    (asset) =>
      asset.risk_level === "HIGH",
  ).length;

  const mediumRisk = assets.filter(
    (asset) =>
      asset.risk_level === "MEDIUM",
  ).length;

  const verified = assets.filter(
    (asset) =>
      asset.identity_status === "VERIFIED",
  ).length;

  // ============================================================
  // Twin model state
  // ============================================================

  const predictionPersisted =
    twin?.ai.prediction_method ===
    "persisted_bridge_ml";

  const researchTransfer =
    twin?.ai.status ===
    "RESEARCH_TRANSFER";

  const modelValidated =
    twin?.ai.model_validated === true;

  function openTwin() {
    if (!selected) {
      return;
    }

    setWorkspace("TWIN");
  }

  // ============================================================
  // Render
  // ============================================================

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">
          S
        </div>

        <div className="brand-copy">
          <strong>SIMRAS</strong>

          <span>
            Infrastructure intelligence · Andhra Pradesh
          </span>
        </div>

        <nav>
          <button
            type="button"
            className={
              workspace === "GIS"
                ? "active"
                : ""
            }
            onClick={() =>
              setWorkspace("GIS")
            }
          >
            GIS command
          </button>

          <button
            type="button"
            className={
              workspace === "TWIN"
                ? "active"
                : ""
            }
            onClick={() =>
              setWorkspace("TWIN")
            }
          >
            Digital twin
          </button>
        </nav>

        <StatusPill
          label="Decision support"
          tone="warn"
        />
      </header>

      <main>
        <section className="hero-row">
          <div>
            <span className="eyebrow">
              AP BRIDGES · DAMS · BARRAGES
            </span>

            <h1>
              {workspace === "GIS"
                ? "Infrastructure risk command"
                : selected?.name ??
                  "Digital twin"}
            </h1>

            <p>
              Every displayed value is associated with
              source, timestamp, quality and confidence.
              Estimated, synthetic and research-transfer
              data are explicitly disclosed.
            </p>
          </div>

          {selected &&
            workspace === "GIS" && (
              <button
                type="button"
                className="primary-action"
                onClick={openTwin}
              >
                Open selected twin →
              </button>
            )}
        </section>

        {error && (
          <div className="error-banner">
            <strong>
              Connection problem
            </strong>

            <span>
              {error}
            </span>

            <button
              type="button"
              onClick={() =>
                setError(undefined)
              }
              aria-label="Dismiss error"
            >
              ×
            </button>
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
            detail={`${mediumRisk} medium-risk assets`}
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
                  onChange={(event) =>
                    setQuery(
                      event.target.value,
                    )
                  }
                  placeholder="Search asset, code or district"
                />

                <select
                  value={typeFilter}
                  onChange={(event) =>
                    setTypeFilter(
                      event.target.value,
                    )
                  }
                >
                  <option value="all">
                    All assets
                  </option>

                  <option value="bridge">
                    Bridges
                  </option>

                  <option value="dam">
                    Dams
                  </option>

                  <option value="barrage">
                    Barrages
                  </option>
                </select>
              </div>

              {loadingAssets ? (
                <p className="loading">
                  Loading canonical registry…
                </p>
              ) : filteredAssets.length > 0 ? (
                <AssetList
                  assets={filteredAssets}
                  selectedCode={
                    selected?.asset_code
                  }
                  onSelect={setSelected}
                />
              ) : (
                <p className="loading">
                  No assets match the current filters.
                </p>
              )}
            </aside>

            <div className="map-stage">
              <GISMap
                assets={filteredAssets}
                mapFeatures={mapFeatures}
                selected={selected}
                onSelect={setSelected}
              />

              <div className="map-layer-control">
                <label htmlFor="map-layer">
                  Context layer
                </label>

                <select
                  id="map-layer"
                  value={mapFeatureType}
                  onChange={(event) =>
                    setMapFeatureType(
                      event.target.value,
                    )
                  }
                >
                  <option value="all">
                    All layers ({mapFeatureTotal})
                  </option>

                  {mapLayers.map(
                    (layer) => (
                      <option
                        key={layer.featureType}
                        value={layer.featureType}
                      >
                        {layer.featureType} ({layer.records})
                      </option>
                    ),
                  )}
                </select>

                <small>
                  {mapLoading
                    ? "Loading layer…"
                    : `Showing ${mapFeatures.features.length} of ${mapFeatures.total}`}
                </small>
              </div>

              <div className="map-legend">
                <span>
                  <i className="low" />
                  Low
                </span>

                <span>
                  <i className="medium" />
                  Medium
                </span>

                <span>
                  <i className="high" />
                  High
                </span>

                <span>
                  <i className="context" />
                  Context
                </span>
              </div>
            </div>
          </section>
        ) : (
          <section className="twin-workspace">
            <div className="twin-header">
              <div>
                <span className="asset-code">
                  {selected?.asset_code ??
                    "NO ASSET"}
                </span>

                <StatusPill
                  label={
                    selected?.identity_status ??
                    "UNKNOWN"
                  }
                  tone={
                    selected?.identity_status ===
                    "VERIFIED"
                      ? "good"
                      : "warn"
                  }
                />
              </div>

              <div className="segmented-control">
                <button
                  type="button"
                  className={
                    viewerMode ===
                    "ASSET_MODEL"
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setViewerMode(
                      "ASSET_MODEL",
                    )
                  }
                >
                  Asset model
                </button>

                <button
                  type="button"
                  className={
                    viewerMode ===
                    "GEOSPATIAL"
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setViewerMode(
                      "GEOSPATIAL",
                    )
                  }
                >
                  Terrain & buildings 3D
                </button>
              </div>
            </div>

            {twin && (
              <div className="twin-model-status">
                <StatusPill
                  label={
                    predictionPersisted
                      ? "PERSISTED AI"
                      : "LIVE / FALLBACK"
                  }
                  tone={
                    predictionPersisted
                      ? "good"
                      : "warn"
                  }
                />

                <StatusPill
                  label={
                    twin.ai.status
                  }
                  tone={
                    modelValidated
                      ? "good"
                      : "warn"
                  }
                />

                {researchTransfer && (
                  <StatusPill
                    label="AP VALIDATION PENDING"
                    tone="warn"
                  />
                )}

                <span>
                  Model:{" "}
                  <strong>
                    {twin.ai.model_version}
                  </strong>
                </span>

                <span>
                  Confidence:{" "}
                  <strong>
                    {twin.ai.confidence != null
                      ? `${Math.round(
                          twin.ai.confidence *
                            100,
                        )}%`
                      : "—"}
                  </strong>
                </span>
              </div>
            )}

            {loadingTwin ? (
              <p className="loading">
                Building canonical twin state…
              </p>
            ) : twin ? (
              <>
                <div className="twin-stage">
                  {viewerMode ===
                  "ASSET_MODEL" ? (
                    <TwinViewer3D
                      twin={twin}
                    />
                  ) : (
                    <CesiumTwinViewer
                      twin={twin}
                    />
                  )}
                </div>

                <TwinPanels
                  twin={twin}
                />
              </>
            ) : selected ? (
              <p className="loading">
                Digital Twin data is unavailable for this asset.
              </p>
            ) : (
              <p className="loading">
                Select an infrastructure asset to open its Digital Twin.
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
