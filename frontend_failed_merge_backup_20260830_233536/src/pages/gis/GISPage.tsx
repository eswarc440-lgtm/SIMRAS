import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { Crosshair, Layers, ListFilter, Search } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Checkbox } from "../../components/ui/checkbox";
import { Label } from "../../components/ui/label";
import { RiskBadge, StatusBadge } from "../../components/common/StatusBadge";
import { gisApi } from "../../services/gisApi";
import { infrastructureService } from "../../services/infrastructureService";
import type { AssetType, InfrastructureAsset } from "../../types";

const GISMap = lazy(() => import("../../components/gis/GISMap"));

// Map real infrastructure types to frontend asset types
const ASSET_TYPE_MAP: Record<string, AssetType> = {
  "dam": "Building",
  "bridge": "Bridge",
  "road": "Road",
  "airport": "Utility",
  "port": "Water",
  "barrage": "Water",
  "flyover": "Bridge",
  "powerplant": "Utility",
  "school": "Building",
  "building": "Building",
  "utility": "Utility",
  "other": "Other",
};

const layerTypes: AssetType[] = ["Bridge", "Road", "Building", "Water", "Utility", "Other"];

function mapAssetType(type: string): AssetType {
  return ASSET_TYPE_MAP[type?.toLowerCase()] || "Other";
}

function getHealthStatus(score: number | null): InfrastructureAsset["health"] {
  if (score === null || score === undefined) return "healthy";
  if (score >= 80) return "healthy";
  if (score >= 50) return "warning";
  return "critical";
}

function getRiskLevel(riskScore: number | null): InfrastructureAsset["risk"] {
  if (riskScore === null || riskScore === undefined) return "low";
  if (riskScore >= 50) return "high";
  if (riskScore >= 25) return "medium";
  return "low";
}

export function GISPage() {
  const [mounted, setMounted] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState<AssetType[]>(layerTypes);
  const [allAssets, setAllAssets] = useState<InfrastructureAsset[]>([]);
  const [selected, setSelected] = useState<InfrastructureAsset | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setMounted(true);

    let isMounted = true;

    // Fetch assets using real backend data
    const fetchAssets = async () => {
      try {
        setLoading(true);

        // Fetch using GeoJSON API to get real coordinates from PostGIS
        const geojson = await gisApi.getAssets({
          limit: 500,
        });

        if (!isMounted) return;

        // Transform GeoJSON features to frontend asset format
        const transformedAssets = geojson.features
          .map((feature) => {
            const props = feature.properties;
            const [lng, lat] = feature.geometry.coordinates;

            return {
              id: props.asset_id || String(props.id),
              asset_id: props.asset_id,
              name: props.name || "Unnamed Asset",
              type: mapAssetType(props.type),
              location: props.location || props.district || "Unknown",
              district: props.district || "Unknown",
              lat: Number(lat),
              lng: Number(lng),
              health: getHealthStatus(Number(props.health_score ?? 0)),
              healthScore: Number(props.health_score ?? 0),
              risk: getRiskLevel(Number(props.risk_score ?? 0)),
              riskScore: Number(props.risk_score ?? 0),
              lastInspection: props.last_inspection_date || "Never",
              status: props.status || "Unknown",
              builtYear: Number(props.built_year ?? 0),
              rulYears: Number(props.remaining_useful_life ?? 0),
              condition: props.condition || "Unknown",
              age: Number(props.age ?? 0),
              material: props.material || "Unknown",
              owner: props.owner || "Unknown",
            };
          })
          .filter((asset) => Number.isFinite(asset.lat) && Number.isFinite(asset.lng))
          .filter((asset) => !(asset.lat === 0 && asset.lng === 0));

        if (!isMounted) return;
        setAllAssets(transformedAssets);
        if (transformedAssets.length > 0) {
          setSelected(transformedAssets[0]);
        }
      } catch (error) {
        console.error("Failed to fetch GIS assets:", error);
        // Fallback: try to fetch from infrastructure endpoint
        try {
          const result = await infrastructureService.list({ limit: 500 });
          if (!isMounted) return;

          const transformedAssets = result.data
            .map((asset) => ({
              id: asset.asset_id || asset.id,
              asset_id: asset.asset_id,
              name: asset.name || "Unnamed Asset",
              type: mapAssetType(asset.asset_type || asset.type),
              location: asset.location || asset.district || "Unknown",
              district: asset.district || "Unknown",
              lat: Number(asset.latitude ?? asset.lat ?? 0),
              lng: Number(asset.longitude ?? asset.lng ?? 0),
              health: getHealthStatus(Number(asset.health_score ?? 0)),
              healthScore: Number(asset.health_score ?? 0),
              risk: getRiskLevel(Number(asset.risk_score ?? 0)),
              riskScore: Number(asset.risk_score ?? 0),
              lastInspection: asset.lastInspection || "Never",
              status: asset.status || "Unknown",
              builtYear: Number(asset.built_year ?? 0),
              rulYears: Number(asset.remaining_useful_life ?? 0),
              condition: asset.condition || "Unknown",
              age: asset.age || 0,
              material: asset.material || "Unknown",
              owner: asset.owner || "Unknown",
            }))
            .filter((asset) => Number.isFinite(asset.lat) && Number.isFinite(asset.lng))
            .filter((asset) => !(asset.lat === 0 && asset.lng === 0));

          setAllAssets(transformedAssets);
          if (transformedAssets.length > 0) {
            setSelected(transformedAssets[0]);
          }
        } catch (fallbackError) {
          console.error("Fallback infrastructure fetch also failed:", fallbackError);
          setAllAssets([]);
          setSelected(undefined);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchAssets();

    return () => {
      isMounted = false;
    };
  }, []);

  const filtered = useMemo(
    () =>
      allAssets.filter(
        (a) =>
          active.includes(a.type) &&
          (a.name.toLowerCase().includes(query.toLowerCase()) || 
           a.id?.toLowerCase().includes(query.toLowerCase()) ||
           a.asset_id?.toLowerCase().includes(query.toLowerCase())),
      ),
    [active, query, allAssets],
  );

  const toggle = (t: AssetType) =>
    setActive((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <div className="relative min-w-0">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search infrastructureâ€¦"
              aria-label="Search infrastructure"
              className="pl-9"
            />
          </div>
          <Button variant="outline" className="shrink-0">
            <ListFilter className="size-4" />
            <span className="hidden sm:inline">Filters</span>
          </Button>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="overflow-hidden rounded-lg border bg-card">
            <div className="h-[52vh] min-h-[380px] lg:h-[calc(100vh-16rem)]">
              {mounted && !loading ? (
                <Suspense fallback={<div className="grid size-full place-items-center text-sm text-muted-foreground">Loading mapâ€¦</div>}>
                  <GISMap assets={filtered} selectedId={selected?.id} onSelect={setSelected} />
                </Suspense>
              ) : (
                <div className="grid size-full place-items-center text-sm text-muted-foreground">
                  {loading ? "Loading real asset data from databaseâ€¦" : "Preparing GIS workspaceâ€¦"}
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 border-t px-4 py-3 text-xs text-muted-foreground">
              <span className="eyebrow">Legend</span>
              <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-success" /> Healthy</span>
              <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-warning" /> Warning</span>
              <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-danger" /> Critical</span>
              <span className="ml-auto flex items-center gap-1.5">
                <Crosshair className="size-3.5" aria-hidden="true" /> {filtered.length} assets shown
              </span>
            </div>
          </div>

          <aside className="space-y-4">
            <section className="rounded-lg border bg-card p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Layers className="size-4" aria-hidden="true" /> Map Layers
              </h2>
              <ul className="mt-3 space-y-2.5">
                {layerTypes.map((t) => (
                  <li key={t} className="flex items-center gap-2.5">
                    <Checkbox id={`layer-${t}`} checked={active.includes(t)} onCheckedChange={() => toggle(t)} />
                    <Label htmlFor={`layer-${t}`} className="text-sm font-normal">
                      {t}
                    </Label>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-lg border bg-card p-4">
              <h2 className="text-sm font-semibold">Asset Details</h2>
              {selected ? (
                <div className="mt-3 space-y-3">
                  <div>
                    <p className="font-mono text-[11px] text-muted-foreground">{selected.id}</p>
                    <p className="text-base font-semibold">{selected.name}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {selected.condition} Â· {selected.type} Â· {selected.location}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge status={selected.health} />
                    <RiskBadge risk={selected.risk} />
                  </div>
                  <dl className="grid grid-cols-2 gap-3 border-t pt-3 text-sm">
                    <div>
                      <dt className="eyebrow text-muted-foreground">Health score</dt>
                      <dd className="mt-1 font-display text-lg font-bold tabular-nums">{selected.healthScore.toFixed(2)}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-muted-foreground">Risk score</dt>
                      <dd className="mt-1 font-display text-lg font-bold tabular-nums">{selected.riskScore.toFixed(2)}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-muted-foreground">Age</dt>
                      <dd className="mt-1">{selected.age} years</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-muted-foreground">RUL</dt>
                      <dd className="mt-1">{selected.rulYears.toFixed(1)} years</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-muted-foreground">Material</dt>
                      <dd className="mt-1">{selected.material}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-muted-foreground">Owner</dt>
                      <dd className="mt-1">{selected.owner}</dd>
                    </div>
                  </dl>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">Select a marker on the map to inspect an asset.</p>
              )}
            </section>
          </aside>
        </div>
      </div>
    </DashboardLayout>
  );
}






