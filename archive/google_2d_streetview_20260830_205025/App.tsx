import { useEffect, useMemo, useState } from "react";
import { AssetList } from "./components/AssetList";
import { GISMap } from "./components/GISMap";
import { KpiCard } from "./components/KpiCard";
import { StatusPill } from "./components/StatusPill";
import { CesiumTwinViewer } from "./features/digital-twin/CesiumTwinViewer";
import { StreetView360 } from "./features/digital-twin/StreetView360";
import { EvidenceStatePanel } from "./features/digital-twin/EvidenceStatePanel";
import { TwinPanels } from "./features/digital-twin/TwinPanels";
import { TwinViewer3D } from "./features/digital-twin/TwinViewer3D";
import { api } from "./services/api";
import {
  getPredictionStatus,
  type PredictionStatus,
} from "./services/predictionStatus";

import type { EvidenceStateResponse } from "./types/evidence";
import type {
  AssetSummary,
  MapFeatureCollection,
  MapFeatureSummaryItem,
  TwinResponse,
} from "./types/twin";

type Workspace = "GIS" | "TWIN";
type ViewerMode = "ASSET_MODEL" | "GEOSPATIAL" | "STREET_360";

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
  const [predictionStatus, setPredictionStatus] =
    useState<PredictionStatus>();
  const [workspace, setWorkspace] = useState<Workspace>("GIS");
  const [viewerMode, setViewerMode] =
    useState<ViewerMode>("ASSET_MODEL");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [districtFilter, setDistrictFilter] = useState("all");
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

    Promise.all([
      api.assets(),
      api.twinCatalog(),
      api.mapSummary(),
    ])
      .then(([response, catalog, mapResponse]) => {
        if (cancelled) return;

        const qualityByCode = new Map(
          catalog.items.map((item) => [
            item.asset_code,
            item,
          ]),
        );

        const ranked = response.items
          .map((asset) => {
            const quality = qualityByCode.get(
              asset.asset_code,
            );

            return {
              ...asset,
              twin_quality_score:
                quality?.twin_quality_score ?? 0,
              twin_quality:
                quality?.twin_quality ?? "BASIC",
              twin_group:
                quality?.twin_group ?? "BASIC",
              twin_quality_label:
                quality?.twin_quality_label ??
                "Source-backed geometry incomplete",
              twin_fidelity:
                quality?.fidelity_level ?? "L0",
              twin_source_backed:
                quality?.source_backed ?? false,
              twin_dimension_count:
                quality?.dimension_count ?? 0,
              twin_template:
                quality?.template ?? "generic",
            };
          })
          .sort((a, b) => {
            const qualityDifference =
              (b.twin_quality_score ?? 0) -
              (a.twin_quality_score ?? 0);

            if (qualityDifference !== 0) {
              return qualityDifference;
            }

            return (
              (b.risk_score ?? -1) -
              (a.risk_score ?? -1)
            );
          });

        setAssets(ranked);
        setMapSummary(mapResponse.items);

        const configuredCode =
          import.meta.env.VITE_DEFAULT_ASSET_ID;

        const configured = ranked.find(
          (asset) =>
            asset.asset_code === configuredCode &&
            (asset.twin_quality_score ?? 0) >= 70,
        );

        const best =
          ranked.find(
            (asset) => asset.twin_group === "BEST",
          ) ?? ranked[0];

        setSelected(configured ?? best);
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
  }, []);
  useEffect(() => {
    let cancelled = false;
    setMapLoading(true);

    api.mapFeatures(
      mapFeatureType === "all" ? undefined : mapFeatureType,
    )
      .then((response) => {
        if (!cancelled) setMapFeatures(response);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof Error ? cause.message : String(cause),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setMapLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [mapFeatureType]);

  useEffect(() => {
    if (!selected) return;

    let cancelled = false;
    const assetCode = selected.asset_code;

    setTwin(undefined);
    setEvidenceState(undefined);
    setPredictionStatus(undefined);
    setError(undefined);

    Promise.allSettled([
      api.twin(assetCode),
      api.state(assetCode),
      getPredictionStatus(assetCode),
    ]).then(
      ([
        twinResult,
        stateResult,
        predictionResult,
      ]) => {
        if (cancelled) return;

        if (twinResult.status === "fulfilled") {
          if (
            twinResult.value.asset.asset_code ===
            assetCode
          ) {
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
        }

        if (
          predictionResult.status ===
          "fulfilled"
        ) {
          if (
            predictionResult.value.asset
              .asset_code === assetCode
          ) {
            setPredictionStatus(
              predictionResult.value,
            );
          }
        }
      },
    );

    return () => {
      cancelled = true;
    };
  }, [selected]);

  const districts = useMemo(
    () =>
      Array.from(
        new Set(
          assets
            .map((asset) => asset.district)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [assets],
  );

  const filteredAssets = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    return assets.filter((asset) => {
      const matchesType =
        typeFilter === "all" || asset.asset_type === typeFilter;

      const matchesDistrict =
        districtFilter === "all" ||
        asset.district === districtFilter;

      const matchesText =
        !normalized ||
        `${asset.name} ${asset.district ?? ""}`
          .toLowerCase()
          .includes(normalized);

      return matchesType && matchesDistrict && matchesText;
    });
  }, [assets, query, typeFilter, districtFilter]);

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
      <header className="topbar">
        <div className="brand-mark">S</div>
        <div className="brand-copy">
          <strong>SIMRAS</strong>
          <span>Infrastructure intelligence Â· Andhra Pradesh</span>
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
        </nav>

        <StatusPill label="Evidence backed" tone="good" />
      </header>

      <main>
        <section className="hero-row">
          <div>
            <span className="eyebrow">
              AP BRIDGES Â· DAMS Â· BARRAGES Â· AIRPORTS Â· TEMPLES
            </span>

            <h1>
              {workspace === "GIS"
                ? "Infrastructure risk command"
                : selected?.name ?? "Digital twin"}
            </h1>

            <p>
              Government observations, official evidence, source,
              timestamp, quality and confidence are shown separately.
              SIMRAS predictions are never presented as official condition.
            </p>
          </div>

          {selected && (
            <button
              className="primary-action"
              onClick={() => setWorkspace("TWIN")}
            >
              Open selected twin â†’
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
            detail="SIMRAS current risk classification"
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
                  <option value="bridge">Bridges</option>
                  <option value="dam">Dams</option>
                  <option value="barrage">Barrages</option>
                  <option value="airport">Airports</option>
                  <option value="temple">Temples</option>
                </select>

                <select
                  value={districtFilter}
                  onChange={(event) =>
                    setDistrictFilter(event.target.value)
                  }
                  aria-label="Filter assets by district"
                >
                  <option value="all">All districts</option>

                  {districts.map((district) => (
                    <option key={district} value={district}>
                      {district}
                    </option>
                  ))}
                </select>
              </div>

              {loading ? (
                <p className="loading">Loading registryâ€¦</p>
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
                mapFeatures={mapFeatures}
                selected={selected}
                onSelect={setSelected}
              />

              <div className="map-layer-control">
                <label htmlFor="map-layer">Context layer</label>

                <select
                  id="map-layer"
                  value={mapFeatureType}
                  onChange={(event) =>
                    setMapFeatureType(event.target.value)
                  }
                >
                  <option value="all">
                    All layers ({mapFeatureTotal})
                  </option>

                  {mapLayers.map((layer) => (
                    <option
                      key={layer.featureType}
                      value={layer.featureType}
                    >
                      {layer.featureType} ({layer.records})
                    </option>
                  ))}
                </select>

                <small>
                  {mapLoading
                    ? "Loading layerâ€¦"
                    : `Showing ${mapFeatures.features.length} of ${mapFeatures.total}`}
                </small>
              </div>

              <div className="map-legend">
                <span><i className="low" />Low</span>
                <span><i className="medium" />Medium</span>
                <span><i className="high" />High</span>
                <span><i className="context" />Context</span>
              </div>
            </div>
          </section>
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

              <div className="segmented-control">
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

                <button
                  className={
                    viewerMode === "STREET_360"
                      ? "active"
                      : ""
                  }
                  onClick={() => setViewerMode("STREET_360")}
                >
                  360? Street View
                </button>
              </div>
            </div>

            {twin ? (
              <>
                <div className="twin-stage">
                  {viewerMode === "ASSET_MODEL" ? (
                    <TwinViewer3D
                      twin={twin}
                      predictionStatus={predictionStatus}
                    />
                  ) : viewerMode === "GEOSPATIAL" ? (
                    <CesiumTwinViewer
                      twin={twin}
                      predictionStatus={predictionStatus}
                    />
                  ) : (
                    <StreetView360 twin={twin} />
                  )}
                </div>


                <TwinPanels twin={twin} predictionStatus={predictionStatus} />

                {evidenceState ? (
                  <EvidenceStatePanel state={evidenceState} />
                ) : (
                  <p className="loading">
                    Loading government evidence stateâ€¦
                  </p>
                )}
              </>
            ) : (
              <p className="loading">
                Building canonical twin stateâ€¦
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
