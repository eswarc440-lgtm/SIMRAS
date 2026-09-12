import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Crosshair,
  Database,
  Layers,
  RefreshCw,
  Search,
} from "lucide-react";

import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Checkbox } from "../../components/ui/checkbox";
import { Label } from "../../components/ui/label";
import { API_BASE_URL } from "../../services/api";

const GISMap = lazy(() => import("../../components/gis/GISMap"));

export interface GISAsset {
  id: string;
  assetCode: string;
  name: string;
  assetType: string;
  district: string | null;
  location: string | null;
  lat: number;
  lng: number;
  condition: string | null;
  status: string | null;
  owner: string | null;
  material: string | null;
  builtYear: number | null;
  age: number | null;
  designLife: number | null;
  healthScore: number | null;
  riskScore: number | null;
  riskLevel: string | null;
  remainingLife: number | null;
  identityStatus: string | null;
  confidenceScore: number | null;
  source: string | null;
}

type BackendResult = {
  items: unknown[];
  source: string;
};

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function asString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text ? text : null;
}

function normalizeType(value: unknown): string {
  const text = String(value ?? "other")
    .trim()
    .toLowerCase()
    .replaceAll("_", " ");

  const aliases: Record<string, string> = {
    "road bridge": "bridge",
    "major road bridge": "bridge",
    "rail bridge": "bridge",
    "flyover": "bridge",
    "reservoir": "dam",
    "powerplant": "power plant",
    "power plant": "power plant",
  };

  return aliases[text] ?? text ?? "other";
}

function featureToRecord(feature: any) {
  const props = feature?.properties ?? {};
  const coordinates = feature?.geometry?.coordinates ?? [];

  return {
    ...props,
    longitude: props.longitude ?? coordinates?.[0],
    latitude: props.latitude ?? coordinates?.[1],
    geometry: feature?.geometry,
  };
}

function extractRecords(payload: any): unknown[] {
  if (Array.isArray(payload)) return payload;

  if (payload?.type === "FeatureCollection" && Array.isArray(payload.features)) {
    return payload.features.map(featureToRecord);
  }

  if (Array.isArray(payload?.features)) {
    return payload.features.map(featureToRecord);
  }

  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.assets)) return payload.assets;
  if (Array.isArray(payload?.results)) return payload.results;

  return [];
}

function normalizeAsset(raw: any): GISAsset | null {
  const lat = asNumber(
    raw?.latitude ??
      raw?.lat ??
      raw?.geometry?.coordinates?.[1] ??
      raw?.centroid?.coordinates?.[1],
  );

  const lng = asNumber(
    raw?.longitude ??
      raw?.lng ??
      raw?.lon ??
      raw?.geometry?.coordinates?.[0] ??
      raw?.centroid?.coordinates?.[0],
  );

  if (lat === null || lng === null || (lat === 0 && lng === 0)) {
    return null;
  }

  const assetCode =
    asString(
      raw?.asset_code ??
        raw?.asset_id ??
        raw?.code ??
        raw?.canonical_code ??
        raw?.id,
    ) ?? `asset-${lat}-${lng}`;

  return {
    id: assetCode,
    assetCode,
    name: asString(raw?.name ?? raw?.asset_name) ?? "Unnamed asset",
    assetType: normalizeType(raw?.asset_type ?? raw?.type ?? raw?.feature_type),
    district: asString(raw?.district),
    location: asString(raw?.location ?? raw?.place),
    lat,
    lng,
    condition: asString(raw?.condition),
    status: asString(raw?.status),
    owner: asString(raw?.owner),
    material: asString(raw?.material),
    builtYear: asNumber(raw?.built_year),
    age: asNumber(raw?.age ?? raw?.current_age),
    designLife: asNumber(raw?.design_life),
    healthScore: asNumber(raw?.health_score),
    riskScore: asNumber(raw?.risk_score),
    riskLevel: asString(raw?.risk_level ?? raw?.predicted_class),
    remainingLife: asNumber(
      raw?.remaining_useful_life ?? raw?.remaining_life ?? raw?.rul_years,
    ),
    identityStatus: asString(raw?.identity_status),
    confidenceScore: asNumber(raw?.confidence_score),
    source: asString(raw?.source ?? raw?.source_name),
  };
}

async function getJson(path: string) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function fetchRealAssets(): Promise<BackendResult> {
  const endpoints = [
    ["/api/v1/assets/geojson", "Asset GeoJSON / PostGIS"],
    ["/api/v1/assets?limit=1000", "Asset registry / PostGIS"],
    ["/api/v1/gis/assets?limit=1000", "GIS compatibility API"],
    ["/api/v1/map/features?limit=1000", "Map features API"],
  ] as const;

  const failures: string[] = [];

  for (const [path, source] of endpoints) {
    try {
      const payload = await getJson(path);
      const items = extractRecords(payload);

      if (items.length > 0) {
        return { items, source };
      }

      failures.push(`${source}: returned 0 records`);
    } catch (error) {
      failures.push(
        `${source}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  throw new Error(
    `No real GIS records were returned. ${failures.join(" | ")}`,
  );
}

function scoreText(value: number | null) {
  return value === null ? "N/A" : value.toFixed(1);
}

function valueText(value: string | number | null, suffix = "") {
  if (value === null || value === undefined || value === "") return "N/A";
  return `${value}${suffix}`;
}

function riskBand(asset: GISAsset): "high" | "medium" | "low" | "unknown" {
  if (asset.riskLevel) {
    const level = asset.riskLevel.toLowerCase();
    if (level.includes("high") || level.includes("critical")) return "high";
    if (level.includes("medium") || level.includes("moderate")) return "medium";
    if (level.includes("low")) return "low";
  }

  if (asset.riskScore === null) return "unknown";
  if (asset.riskScore >= 70) return "high";
  if (asset.riskScore >= 40) return "medium";
  return "low";
}

export function GISPage() {
  const [query, setQuery] = useState("");
  const [allAssets, setAllAssets] = useState<GISAsset[]>([]);
  const [selected, setSelected] = useState<GISAsset | undefined>();
  const [activeTypes, setActiveTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<string>("Backend");
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const result = await fetchRealAssets();

        const normalized = result.items
          .map(normalizeAsset)
          .filter((item): item is GISAsset => item !== null)
          .filter(
            (item) =>
              item.lat >= 12.0 &&
              item.lat <= 20.5 &&
              item.lng >= 76.0 &&
              item.lng <= 86.0,
          );

        const deduped = Array.from(
          new Map(normalized.map((item) => [item.assetCode, item])).values(),
        );

        if (cancelled) return;

        setAllAssets(deduped);
        setDataSource(result.source);

        const types = Array.from(
          new Set(deduped.map((item) => item.assetType)),
        ).sort();

        setActiveTypes(types);
        setSelected(deduped[0]);
      } catch (reason) {
        if (cancelled) return;
        setAllAssets([]);
        setSelected(undefined);
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  const layerTypes = useMemo(
    () => Array.from(new Set(allAssets.map((asset) => asset.assetType))).sort(),
    [allAssets],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return allAssets.filter((asset) => {
      if (!activeTypes.includes(asset.assetType)) return false;
      if (!q) return true;

      return [
        asset.assetCode,
        asset.name,
        asset.assetType,
        asset.district ?? "",
        asset.location ?? "",
      ].some((value) => value.toLowerCase().includes(q));
    });
  }, [activeTypes, allAssets, query]);

  function toggleLayer(type: string) {
    setActiveTypes((current) =>
      current.includes(type)
        ? current.filter((item) => item !== type)
        : [...current, type],
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <section className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative min-w-0 flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search infrastructure..."
              aria-label="Search infrastructure"
              className="h-11 pl-9"
            />
          </div>

          <Button
            type="button"
            variant="outline"
            className="shrink-0"
            onClick={() => setRefreshToken((value) => value + 1)}
            disabled={loading}
          >
            <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
            Refresh real data
          </Button>
        </section>

        <section className="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-4 py-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Database className="size-3.5" />
            Source: <strong className="text-foreground">{dataSource}</strong>
          </span>
          <span>{allAssets.length.toLocaleString()} assets with coordinates</span>
          <span>{layerTypes.length} infrastructure types</span>
          {error && (
            <span className="flex items-center gap-1.5 text-destructive">
              <AlertTriangle className="size-3.5" />
              {error}
            </span>
          )}
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_330px]">
          <div className="overflow-hidden rounded-lg border bg-card">
            <div className="h-[calc(100vh-270px)] min-h-[520px]">
              {loading ? (
                <div className="grid size-full place-items-center text-sm text-muted-foreground">
                  Loading real infrastructure coordinates from backend...
                </div>
              ) : error ? (
                <div className="grid size-full place-items-center p-8">
                  <div className="max-w-xl text-center">
                    <AlertTriangle className="mx-auto size-7 text-destructive" />
                    <h2 className="mt-3 font-semibold">GIS data connection failed</h2>
                    <p className="mt-2 text-sm text-muted-foreground">{error}</p>
                    <p className="mt-3 text-xs text-muted-foreground">
                      No demonstration markers are inserted when backend data is unavailable.
                    </p>
                  </div>
                </div>
              ) : (
                <Suspense
                  fallback={
                    <div className="grid size-full place-items-center text-sm text-muted-foreground">
                      Loading map...
                    </div>
                  }
                >
                  <GISMap
                    assets={filtered}
                    selectedId={selected?.id}
                    onSelect={setSelected}
                  />
                </Suspense>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 border-t px-4 py-3 text-xs text-muted-foreground">
              <span className="eyebrow">Risk legend</span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-500" /> Low
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-amber-500" /> Medium
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-red-500" /> High
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-slate-500" /> N/A
              </span>
              <span className="ml-auto flex items-center gap-1.5">
                <Crosshair className="size-3.5" />
                {filtered.length.toLocaleString()} assets shown
              </span>
            </div>
          </div>

          <aside className="space-y-4">
            <section className="rounded-lg border bg-card p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Layers className="size-4" />
                Real infrastructure layers
              </h2>

              {layerTypes.length > 0 ? (
                <ul className="mt-3 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
                  {layerTypes.map((type) => {
                    const count = allAssets.filter(
                      (asset) => asset.assetType === type,
                    ).length;

                    return (
                      <li key={type} className="flex items-center gap-2.5">
                        <Checkbox
                          id={`layer-${type}`}
                          checked={activeTypes.includes(type)}
                          onCheckedChange={() => toggleLayer(type)}
                        />
                        <Label
                          htmlFor={`layer-${type}`}
                          className="flex min-w-0 flex-1 items-center justify-between gap-3 text-sm font-normal"
                        >
                          <span className="capitalize">{type}</span>
                          <span className="text-xs text-muted-foreground">
                            {count}
                          </span>
                        </Label>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  No mapped infrastructure types returned by the backend.
                </p>
              )}
            </section>

            <section className="rounded-lg border bg-card p-4">
              <h2 className="text-sm font-semibold">Asset details</h2>

              {selected ? (
                <div className="mt-3 space-y-4">
                  <div>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {selected.assetCode}
                    </p>
                    <p className="mt-1 text-base font-semibold">{selected.name}</p>
                    <p className="mt-1 text-sm capitalize text-muted-foreground">
                      {selected.assetType}
                      {" · "}
                      {selected.district ?? selected.location ?? "Location N/A"}
                    </p>
                  </div>

                  <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-t pt-4 text-sm">
                    <div>
                      <dt className="text-xs text-muted-foreground">Health</dt>
                      <dd className="mt-1 font-semibold">
                        {scoreText(selected.healthScore)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Risk</dt>
                      <dd className="mt-1 font-semibold capitalize">
                        {selected.riskScore !== null
                          ? `${selected.riskScore.toFixed(1)} (${riskBand(selected)})`
                          : selected.riskLevel ?? "N/A"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Condition</dt>
                      <dd className="mt-1">{selected.condition ?? "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Identity</dt>
                      <dd className="mt-1">{selected.identityStatus ?? "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Built year</dt>
                      <dd className="mt-1">{valueText(selected.builtYear)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Age</dt>
                      <dd className="mt-1">
                        {valueText(selected.age, selected.age !== null ? " years" : "")}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Design life</dt>
                      <dd className="mt-1">
                        {valueText(
                          selected.designLife,
                          selected.designLife !== null ? " years" : "",
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">RUL</dt>
                      <dd className="mt-1">
                        {valueText(
                          selected.remainingLife,
                          selected.remainingLife !== null ? " years" : "",
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Material</dt>
                      <dd className="mt-1">{selected.material ?? "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Owner</dt>
                      <dd className="mt-1">{selected.owner ?? "N/A"}</dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-xs text-muted-foreground">Coordinates</dt>
                      <dd className="mt-1 font-mono text-xs">
                        {selected.lat.toFixed(6)}, {selected.lng.toFixed(6)}
                      </dd>
                    </div>
                  </dl>

                  <a
                    href={`/digital-twin?asset=${encodeURIComponent(selected.assetCode)}`}
                    className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
                  >
                    Open Digital Twin
                  </a>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Select a real asset marker on the map.
                </p>
              )}
            </section>
          </aside>
        </div>
      </div>
    </DashboardLayout>
  );
}
