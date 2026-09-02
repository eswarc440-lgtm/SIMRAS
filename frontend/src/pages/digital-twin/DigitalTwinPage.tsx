import RealityTwinAssetViewer from "../../features/digital-twin/RealityTwinAssetViewer";
import { useEffect, useMemo, useState } from "react";

import { Search } from "lucide-react";

import { DashboardLayout } from "../../layouts/DashboardLayout";

import { Input } from "../../components/ui/input";

import { api as twinApi } from "../../services/simrasTwinApi";

import { TwinViewer3D } from "../../features/digital-twin/TwinViewer3D";

import { GoogleMapStreetView } from "../../features/digital-twin/GoogleMapStreetView";

import { TwinPanels } from "../../features/digital-twin/TwinPanels";



import OpenPublicRealityTwin from "../../components/realityTwin/OpenPublicRealityTwin";
import type {
  AssetSummary,
  TwinResponse,
} from "../../types/twin";

import type {
  EvidenceStateResponse,
} from "../../types/evidence";


type Mode =
  | "ASSET_MODEL"
  | "MAP_2D"
  | "GEOSPATIAL";


const workspaceHeight =
  "clamp(520px, calc(100vh - 220px), 720px)";

const ALL = "ALL";

function rankTwins(items: AssetSummary[]) {
  return [...items].sort((left, right) => {
    const qualityDifference =
      (right.twin_quality_score ?? 0) -
      (left.twin_quality_score ?? 0);

    if (qualityDifference !== 0) return qualityDifference;

    const riskDifference =
      (right.risk_score ?? -1) - (left.risk_score ?? -1);

    if (riskDifference !== 0) return riskDifference;
    return left.name.localeCompare(right.name);
  });
}


export function DigitalTwinPage() {
  const [
    assets,
    setAssets,
  ] = useState<AssetSummary[]>([]);

  const [
    selectedCode,
    setSelectedCode,
  ] = useState<string>();

  const [
    twin,
    setTwin,
  ] = useState<TwinResponse>();

  const [
    evidence,
    setEvidence,
  ] = useState<EvidenceStateResponse>();

  const [
    mode,
    setMode,
  ] = useState<Mode>("ASSET_MODEL");

  const [
    query,
    setQuery,
  ] = useState("");

  const [districtFilter, setDistrictFilter] = useState(ALL);
  const [assetTypeFilter, setAssetTypeFilter] = useState(ALL);
  const [fidelityFilter, setFidelityFilter] = useState(ALL);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    twinLoading,
    setTwinLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string>();


  useEffect(() => {
    twinApi
      .assets()
      .then((response) => {
        const items = rankTwins(response.items ?? []);

        setAssets(items);

        if (items.length) {
          setSelectedCode(
            items[0].asset_code,
          );
        }
      })
      .catch((reason) => {
        setError(String(reason));
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);


  useEffect(() => {
    if (!selectedCode) {
      return;
    }

    setError(undefined);
    setTwinLoading(true);
    setTwin(undefined);
    setEvidence(undefined);

    Promise.allSettled([
      twinApi.twin(selectedCode),
      twinApi.state(selectedCode),
    ])
      .then(
        ([
          twinResult,
          stateResult,
        ]) => {
          if (
            twinResult.status ===
            "fulfilled"
          ) {
            setTwin(
              twinResult.value,
            );
          } else {
            setError(
              String(
                twinResult.reason,
              ),
            );
          }

          if (
            stateResult.status ===
            "fulfilled"
          ) {
            setEvidence(
              stateResult.value,
            );
          }
        },
      )
      .finally(() => {
        setTwinLoading(false);
      });
  }, [selectedCode]);


  const filtered =
    useMemo(() => {
      const normalized =
        query
          .trim()
          .toLowerCase();

      return assets.filter((asset) => {
        const matchesQuery =
          `${asset.asset_code ?? ""}
           ${asset.name ?? ""}
           ${asset.asset_type ?? ""}
           ${asset.district ?? ""}`
            .toLowerCase()
            .includes(normalized);
        const matchesDistrict =
          districtFilter === ALL || asset.district === districtFilter;
        const matchesType =
          assetTypeFilter === ALL || asset.asset_type === assetTypeFilter;
        const fidelity = asset.twin_fidelity ?? "L0";
        const matchesFidelity =
          fidelityFilter === ALL ||
          (fidelityFilter === "STRONG" && fidelity !== "L0") ||
          (fidelityFilter === "L0" && fidelity === "L0");

        return (
          matchesQuery &&
          matchesDistrict &&
          matchesType &&
          matchesFidelity
        );
      });
    }, [assets, assetTypeFilter, districtFilter, fidelityFilter, query]);

  const districts = useMemo(
    () =>
      Array.from(
        new Set(
          assets
            .map((asset) => asset.district)
            .filter((district): district is string => Boolean(district)),
        ),
      ).sort(),
    [assets],
  );

  const assetTypes = useMemo(
    () =>
      Array.from(new Set(assets.map((asset) => asset.asset_type))).sort(),
    [assets],
  );

  useEffect(() => {
    if (filtered.length === 0) {
      setSelectedCode(undefined);
      setTwin(undefined);
    } else if (!filtered.some((asset) => asset.asset_code === selectedCode)) {
      setSelectedCode(filtered[0].asset_code);
    }
  }, [filtered, selectedCode]);


  const selectedAsset =
    useMemo(
      () =>
        assets.find(
          (asset) =>
            asset.asset_code ===
            selectedCode,
        ),
      [
        assets,
        selectedCode,
      ],
    );


  return (
    <DashboardLayout>
      <div className="simras-digital-twin-page">

        {/* ====================================== */}
        {/* PAGE HEADER                            */}
        {/* ====================================== */}

        <header className="simras-twin-page-header">
          <div className="min-w-0">
            <p className="eyebrow text-muted-foreground">
              REAL ASSET WORKSPACE
            </p>

            <h1 className="mt-1 text-2xl font-bold tracking-tight">
              Infrastructure Digital Twin
            </h1>

            {selectedAsset && (
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {selectedAsset.asset_code}
                {" / "}
                {selectedAsset.name}
                {" / "}
                {selectedAsset.district ?? "District N/A"}
              </p>
            )}
          </div>


          <div
            className="
              simras-view-mode
              hidden
              shrink-0
              rounded-lg
              border
              bg-background
              p-1
            "
          >
            {([
              [
                "ASSET_MODEL",
                "Asset model",
              ],
              [
                "MAP_2D",
                "2D map",
              ],
              [
                "GEOSPATIAL",
                "Terrain & buildings 3D",
              ],
            ] as const).map(
              ([
                value,
                label,
              ]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    setMode(value)
                  }
                  className={
                    mode === value
                      ? "active"
                      : ""
                  }
                >
                  {label}
                </button>
              ),
            )}
          </div>
        </header>


        {/* ====================================== */}
        {/* MAIN WORKSPACE                         */}
        {/* ====================================== */}

        <div
          className="
            simras-twin-workspace
            grid
            min-h-0
            gap-4
            xl:grid-cols-[300px_minmax(0,1fr)]
          "
        >

          {/* ==================================== */}
          {/* ASSET SIDEBAR                        */}
          {/* ==================================== */}

          <aside
            className="
              simras-asset-sidebar
              flex
              min-h-0
              flex-col
              overflow-hidden
              rounded-xl
              border
              bg-card
            "
            style={{
              height:
                workspaceHeight,
            }}
          >
            <div
              className="
                border-b
                bg-card
                p-3
              "
            >
              <div className="relative">
                <Search
                  className="
                    pointer-events-none
                    absolute
                    left-3
                    top-1/2
                    size-4
                    -translate-y-1/2
                    text-muted-foreground
                  "
                />

                <Input
                  value={query}
                  onChange={(event) =>
                    setQuery(
                      event.target.value,
                    )
                  }
                  placeholder="Search asset..."
                  className="
                    h-10
                    bg-background
                    pl-9
                  "
                />
              </div>

              <div className="mt-2 grid grid-cols-1 gap-2">
                <select
                  aria-label="Filter by district"
                  className="h-9 rounded-md border bg-background px-2 text-xs"
                  value={districtFilter}
                  onChange={(event) => setDistrictFilter(event.target.value)}
                >
                  <option value={ALL}>All districts</option>
                  {districts.map((district) => (
                    <option key={district} value={district}>
                      {district}
                    </option>
                  ))}
                </select>

                <div className="grid grid-cols-2 gap-2">
                  <select
                    aria-label="Filter by asset type"
                    className="h-9 rounded-md border bg-background px-2 text-xs"
                    value={assetTypeFilter}
                    onChange={(event) => setAssetTypeFilter(event.target.value)}
                  >
                    <option value={ALL}>All types</option>
                    {assetTypes.map((assetType) => (
                      <option key={assetType} value={assetType}>
                        {assetType}
                      </option>
                    ))}
                  </select>

                  <select
                    aria-label="Filter by twin fidelity"
                    className="h-9 rounded-md border bg-background px-2 text-xs"
                    value={fidelityFilter}
                    onChange={(event) => setFidelityFilter(event.target.value)}
                  >
                    <option value={ALL}>All twins</option>
                    <option value="STRONG">Strong twins</option>
                    <option value="L0">L0 fallback</option>
                  </select>
                </div>
              </div>

              <div
                className="
                  mt-2
                  flex
                  items-center
                  justify-between
                  px-1
                  text-[11px]
                  text-muted-foreground
                "
              >
                <span>
                  Real asset registry
                </span>

                <span>
                  {filtered.length}
                  {" / "}
                  {assets.length}
                </span>
              </div>
            </div>


            <div
              className="
                simras-asset-scroll
                min-h-0
                flex-1
                overflow-y-auto
                p-2
              "
            >
              {loading ? (
                <div
                  className="
                    grid
                    h-32
                    place-items-center
                    text-sm
                    text-muted-foreground
                  "
                >
                  Loading assets?
                </div>
              ) : filtered.length === 0 ? (
                <div
                  className="
                    grid
                    h-32
                    place-items-center
                    px-4
                    text-center
                    text-sm
                    text-muted-foreground
                  "
                >
                  No matching assets.
                </div>
              ) : (
                filtered.map(
                  (asset) => {
                    const selected =
                      selectedCode ===
                      asset.asset_code;

                    return (
                      <button
                        key={
                          asset.asset_code
                        }
                        type="button"
                        onClick={() =>
                          setSelectedCode(
                            asset.asset_code,
                          )
                        }
                        className={`
                          simras-asset-row
                          ${
                            selected
                              ? "selected"
                              : ""
                          }
                        `}
                      >
                        <span className="simras-asset-code">
                          {
                            asset.asset_code
                          }
                        </span>

                        <span className="float-right rounded-full border px-1.5 py-0.5 text-[9px] font-semibold">
                          {asset.twin_fidelity ?? "L0"}
                          {asset.twin_group === "BEST" ? " / BEST" : ""}
                        </span>

                        <strong>
                          {
                            asset.name ??
                            "Unnamed asset"
                          }
                        </strong>

                        <small>
                          {
                            asset.asset_type ??
                            "Asset"
                          }
                          {" / "}
                          {
                            asset.district ??
                            "District N/A"
                          }
                        </small>
                      </button>
                    );
                  },
                )
              )}
            </div>
          </aside>


          {/* ==================================== */}
          {/* VIEWER AREA                          */}
          {/* ==================================== */}

          <main className="min-w-0">

            <section
              className="
                simras-twin-card
                flex
                min-h-0
                flex-col
                overflow-hidden
                rounded-xl
                border
                bg-card
              "
              style={{
                height:
                  workspaceHeight,
              }}
            >

              {/* Viewer title strip */}

              <div
                className="
                  simras-viewer-titlebar
                  flex
                  shrink-0
                  items-center
                  justify-between
                  gap-4
                  border-b
                  bg-card
                  px-4
                "
              >
                <div className="min-w-0">
                  <strong
                    className="
                      block
                      truncate
                      text-sm
                    "
                  >
                    {twin?.asset.name ??
                      selectedAsset?.name ??
                      "Digital Twin"}
                  </strong>

                  <span
                    className="
                      block
                      truncate
                      text-[11px]
                      text-muted-foreground
                    "
                  >
                    {selectedCode ??
                      "No asset selected"}
                  </span>
                </div>


                {twin && (
                  <div
                    className="
                      flex
                      shrink-0
                      items-center
                      gap-2
                      text-[11px]
                    "
                  >
                    <span className="rounded-full border px-2 py-1 text-muted-foreground">
                      {
                        twin.asset
                          .asset_type
                      }
                    </span>

                    <span className="rounded-full border px-2 py-1 font-medium">
                      {
                        twin.twin
                          .fidelity_level
                      }
                    </span>
                  </div>
                )}
              </div>


              {/* Viewer */}

              <div
                className="
                  simras-twin-viewer-stage
                  relative
                  min-h-0
                  flex-1
                  overflow-hidden
                  bg-[#07111c]
                "
              >
                {loading ||
                twinLoading ? (
                  <div
                    className="
                      grid
                      h-full
                      place-items-center
                      text-sm
                      text-slate-300
                    "
                  >
                    Loading digital twin?
                  </div>
                ) : error ? (
                  <div
                    className="
                      grid
                      h-full
                      place-items-center
                      p-8
                    "
                  >
                    <div className="max-w-xl text-center">
                      <strong className="text-sm text-red-500">
                        Twin connection problem
                      </strong>

                      <p className="mt-2 break-words text-xs text-muted-foreground">
                        {error}
                      </p>
                    </div>
                  </div>
                ) : !twin ? (
                  <div
                    className="
                      grid
                      h-full
                      place-items-center
                      text-sm
                      text-slate-300
                    "
                  >
                    Select an asset.
                  </div>
                ) : (
                  <>
                    {mode ===
                      "ASSET_MODEL" && (
                      <RealityTwinAssetViewer assetCode={selectedAsset?.asset_code} />
                    )}

                    {mode ===
                      "MAP_2D" && (
                      <GoogleMapStreetView
                        twin={twin}
                      />
                    )}

                    {mode ===
                      "GEOSPATIAL" && (
                      <OpenPublicRealityTwin assetCode={selectedAsset?.asset_code} />
                    )}
                  </>
                )}
              </div>
            </section>
          </main>
        </div>


        {/* ====================================== */}
        {/* REAL BACKEND PANELS                    */}
        {/* ====================================== */}

        {twin && (
          <div className="mt-5">
            <TwinPanels
              twin={twin}
            />
          </div>
        )}

        {evidence && (
          <div className="mt-5">
            
{/* Evidence dashboard removed */}

          </div>
        )}

      </div>
    </DashboardLayout>
  );
}
