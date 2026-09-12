$ErrorActionPreference = "Stop"
$repo = "D:\simras-digital-twin-repository\simras-digital-twin"
Set-Location $repo
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
Write-Host "=== SIMRAS UI INTEGRATION START ===" -ForegroundColor Cyan

# 1) Locate uploaded UI zip
$candidates = @(
    (Join-Path $repo "src(1).zip"),
    (Join-Path $repo "src.zip"),
    (Join-Path $env:USERPROFILE "Downloads\src(1).zip"),
    (Join-Path $env:USERPROFILE "Downloads\src.zip")
)
$zip = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $zip) {
    throw "Put src(1).zip in the repository root or Downloads folder, then run this script again."
}
Write-Host "UI ZIP: $zip"

# 2) Backup current working frontend before touching it
$backup = Join-Path $repo "frontend_backup_$stamp"
Copy-Item ".\frontend" $backup -Recurse -Force
Set-Content ".\.last_frontend_backup.txt" $backup -Encoding UTF8
Write-Host "BACKUP: $backup" -ForegroundColor Green

# Preserve the currently working SIMRAS API client for the real twin.
Copy-Item ".\frontend\src\services\api.ts" ".\frontend\src\services\simrasTwinApi.ts" -Force

# 3) Overlay the new visual frontend WITHOUT deleting the working twin feature directory
$temp = Join-Path $env:TEMP "simras_ui_$stamp"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $temp -Force
if (-not (Test-Path (Join-Path $temp "src"))) { throw "ZIP does not contain src/" }
Copy-Item (Join-Path $temp "src\*") ".\frontend\src\" -Recurse -Force

# Remove TanStack Start server-only entrypoints; this project continues as the existing Vite SPA.
Remove-Item ".\frontend\src\start.ts" -Force -ErrorAction SilentlyContinue
Remove-Item ".\frontend\src\server.ts" -Force -ErrorAction SilentlyContinue

# 4) Convert generated route tree from Start-specific augmentation to browser SPA
$rt = ".\frontend\src\routeTree.gen.ts"
if (Test-Path $rt) {
    $txt = Get-Content $rt -Raw
    $txt = $txt -replace "(?s)\r?\nimport type \{ startInstance \} from './start\.ts'.*$", ""
    Set-Content $rt $txt -Encoding UTF8
}

# 5) Browser root route
@'
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, Outlet, createRootRouteWithContext, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { AuthProvider } from "../hooks/useAuth";

function NotFoundComponent() {
  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold">404</h1>
        <p className="mt-3 text-muted-foreground">Page not found.</p>
        <Link to="/dashboard" className="mt-5 inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground">Dashboard</Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  useEffect(() => console.error(error), [error]);
  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold">This page did not load</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <button className="mt-5 rounded-md bg-primary px-4 py-2 text-primary-foreground" onClick={() => { router.invalidate(); reset(); }}>Try again</button>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </QueryClientProvider>
  );
}
'@ | Set-Content ".\frontend\src\routes\__root.tsx" -Encoding UTF8

# 6) Vite browser entrypoint
@'
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { getRouter } from "./router";
import "./styles.css";

const router = getRouter();
const root = document.getElementById("root");
if (!root) throw new Error("#root element not found");
ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
'@ | Set-Content ".\frontend\src\main.tsx" -Encoding UTF8

# 7) API adapter: new UI uses /api/v1/* while the existing real twin client uses VITE_API_BASE_URL=/api/v1
@'
const configured =
  import.meta.env.VITE_BACKEND_URL ??
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";

export const API_BASE_URL = configured.replace(/\/api\/v1\/?$/, "");

export interface ApiError { status: number; message: string; }

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok) {
    let detail = "Request failed";
    try { const payload = await response.json(); detail = payload?.detail ?? payload?.message ?? JSON.stringify(payload); }
    catch { detail = await response.text(); }
    throw { status: response.status, message: detail } as ApiError;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function mockRequest<T>(data: T, latency = 0): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), latency));
}
'@ | Set-Content ".\frontend\src\services\api.ts" -Encoding UTF8

# Ensure legacy twin API sees the existing /api/v1 base.
if (-not (Test-Path ".\frontend\.env.local")) { New-Item ".\frontend\.env.local" -ItemType File | Out-Null }
$envText = Get-Content ".\frontend\.env.local" -Raw -ErrorAction SilentlyContinue
if ($envText -notmatch "VITE_API_BASE_URL") { Add-Content ".\frontend\.env.local" "VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1" }
if ($envText -notmatch "VITE_BACKEND_URL") { Add-Content ".\frontend\.env.local" "VITE_BACKEND_URL=http://127.0.0.1:8000" }

# 8) Use the EXISTING working SIMRAS twin inside the new UI shell.
@'
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
                  <div className="text-xs text-muted-foreground">{asset.asset_type} · {asset.district}</div>
                </button>
              ))}
            </div>
          </aside>

          <main className="min-w-0 space-y-4">
            <section className="overflow-hidden rounded-lg border bg-card">
              {loading ? <div className="grid h-[620px] place-items-center">Loading assets…</div> : error ? <div className="grid h-[620px] place-items-center p-6 text-danger">{error}</div> : !twin ? <div className="grid h-[620px] place-items-center">Select an asset.</div> : (
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
'@ | Set-Content ".\frontend\src\pages\digital-twin\DigitalTwinPage.tsx" -Encoding UTF8

# 9) Fix uploaded design assets that reference Lovable-only URLs.
$indexRoute = ".\frontend\src\routes\index.tsx"
if (Test-Path $indexRoute) {
  $x = Get-Content $indexRoute -Raw
  $x = $x -replace 'import heroVideo from .*?;\r?\n', ''
  $x = $x -replace '<Hero videoSrc=\{heroVideo\.url\} />', '<Hero />'
  Set-Content $indexRoute $x -Encoding UTF8
}

# Fix old react-three-fiber package name.
Get-ChildItem ".\frontend\src" -Recurse -File -Include *.ts,*.tsx | ForEach-Object {
  $x = Get-Content $_.FullName -Raw
  if ($x -match 'react-three-fiber') {
    $x = $x.Replace('"react-three-fiber"', '"@react-three/fiber"')
    Set-Content $_.FullName $x -Encoding UTF8
  }
}

# Convert @/ imports to relative imports so we do not disturb your existing Cesium Vite config.
@'
from pathlib import Path
import os, re
root = Path("frontend/src").resolve()
for p in root.rglob("*"):
    if p.suffix not in {".ts", ".tsx"}: continue
    text = p.read_text(encoding="utf-8-sig")
    def repl(m):
        target = root / m.group(1)
        rel = os.path.relpath(target, p.parent).replace("\\", "/")
        if not rel.startswith("."): rel = "./" + rel
        return m.group(0).replace("@/" + m.group(1), rel)
    text = re.sub(r'from\s+(["\'])@/([^"\']+)\1', lambda m: f'from {m.group(1)}' + (lambda r: r if r.startswith(".") else "./"+r)(os.path.relpath(root / m.group(2), p.parent).replace("\\","/")) + m.group(1), text)
    text = re.sub(r'import\s+(["\'])@/([^"\']+)\1', lambda m: f'import {m.group(1)}' + (lambda r: r if r.startswith(".") else "./"+r)(os.path.relpath(root / m.group(2), p.parent).replace("\\","/")) + m.group(1), text)
    p.write_text(text, encoding="utf-8")
'@ | py -

# Small styling bridge for the existing real twin panels.
@'
.clean-twin-panels{display:grid;gap:1rem}.clean-score-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem}.clean-score-grid>div,.clean-panel{border:1px solid var(--color-border);background:var(--color-card);border-radius:.65rem;padding:1rem}.clean-score-grid span,.clean-score-grid small{display:block;color:var(--color-muted-foreground);font-size:.75rem}.clean-score-grid strong{display:block;font-size:1.45rem;margin:.25rem 0}.clean-panel h3{font-weight:700}.clean-data-table{width:100%;margin-top:.75rem;border-collapse:collapse;font-size:.875rem}.clean-data-table th,.clean-data-table td{border-bottom:1px solid var(--color-border);padding:.55rem;text-align:left}.clean-two-column{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.clean-list{margin:.75rem 0 0 1rem;list-style:disc}.clean-kicker{font-size:.7rem;letter-spacing:.12em;color:var(--color-muted-foreground)}.clean-note{margin-top:.75rem;color:var(--color-muted-foreground);font-size:.75rem}@media(max-width:900px){.clean-score-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.clean-two-column{grid-template-columns:1fr}}
'@ | Add-Content ".\frontend\src\styles.css" -Encoding UTF8

# 10) Tailwind 4 PostCSS configuration required by the uploaded design.
@'
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
'@ | Set-Content ".\frontend\postcss.config.mjs" -Encoding UTF8

# 11) Backend compatibility API for the new pages.
@'
from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO, StringIO
import csv
import html
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import Asset, Inspection, Maintenance, Prediction

router = APIRouter(tags=["ui-compat"])


def _value(obj, *names, default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _risk_level(score):
    if score is None:
        return "UNKNOWN"
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"


async def _prediction_index(session: AsyncSession):
    rows = (await session.scalars(select(Prediction).order_by(desc(Prediction.prediction_time)))).all()
    index = {}
    for row in rows:
        key = (row.asset_id, str(row.target).lower())
        index.setdefault(key, row)
    return index


def _asset_payload(asset, predictions=None):
    predictions = predictions or {}
    health = predictions.get((asset.id, "health"))
    risk = predictions.get((asset.id, "risk"))
    rul = predictions.get((asset.id, "rul")) or predictions.get((asset.id, "remaining_life"))
    health_score = _value(health, "value")
    risk_score = _value(risk, "value")
    rul_value = _value(rul, "value")
    asset_code = str(_value(asset, "asset_code", default=asset.id))
    return {
        "id": asset_code,
        "asset_id": asset_code,
        "asset_code": asset_code,
        "name": _value(asset, "name", default=asset_code),
        "type": _value(asset, "asset_type", "type", default="other"),
        "asset_type": _value(asset, "asset_type", "type", default="other"),
        "district": _value(asset, "district", default="Unknown"),
        "location": _value(asset, "district", default="Unknown"),
        "latitude": _value(asset, "latitude", "lat"),
        "longitude": _value(asset, "longitude", "lng", "lon"),
        "lat": _value(asset, "latitude", "lat"),
        "lng": _value(asset, "longitude", "lng", "lon"),
        "built_year": _value(asset, "built_year"),
        "design_life": _value(asset, "design_life", "design_life_years"),
        "age": _value(asset, "current_age", "age"),
        "condition": _value(asset, "condition", default="UNKNOWN"),
        "owner": _value(asset, "owner", default="Unknown"),
        "material": _value(asset, "material", default="Unknown"),
        "identity_status": _value(asset, "identity_status", default="UNKNOWN"),
        "status": _value(asset, "status", default="Operational"),
        "health_score": health_score,
        "risk_score": risk_score,
        "risk_level": _value(risk, "predicted_class", default=_risk_level(risk_score)),
        "remaining_useful_life": rul_value,
        "prediction_time": _iso(_value(risk, "prediction_time") or _value(health, "prediction_time")),
        "prediction_confidence": _value(risk, "confidence_score") or _value(health, "confidence_score"),
    }


async def _find_asset(session: AsyncSession, identifier: str):
    stmt = select(Asset).where(Asset.asset_code == identifier)
    if identifier.isdigit():
        stmt = select(Asset).where(or_(Asset.asset_code == identifier, Asset.id == int(identifier)))
    asset = await session.scalar(stmt)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {identifier} not found")
    return asset


@router.get("/infrastructure")
async def infrastructure_list(
    limit: int = Query(100, ge=1, le=5000),
    skip: int = Query(0, ge=0),
    asset_type: str | None = None,
    district: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Asset)
    count_stmt = select(func.count()).select_from(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
        count_stmt = count_stmt.where(Asset.asset_type == asset_type)
    if district and hasattr(Asset, "district"):
        stmt = stmt.where(Asset.district == district)
        count_stmt = count_stmt.where(Asset.district == district)
    total = int(await session.scalar(count_stmt) or 0)
    assets = (await session.scalars(stmt.order_by(Asset.id).offset(skip).limit(limit))).all()
    predictions = await _prediction_index(session)
    return {"total": total, "limit": limit, "skip": skip, "items": [_asset_payload(a, predictions) for a in assets]}


@router.get("/infrastructure/summary")
async def infrastructure_summary(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset))).all()
    counts = Counter(str(_value(a, "asset_type", default="other")).lower() for a in assets)
    return {"total": len(assets), "by_type": dict(counts)}


@router.get("/infrastructure/{identifier}")
async def infrastructure_detail(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    return _asset_payload(asset, predictions)


@router.get("/gis/assets")
async def gis_assets(
    limit: int = Query(500, ge=1, le=5000),
    asset_type: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    assets = (await session.scalars(stmt.order_by(Asset.id).limit(limit))).all()
    predictions = await _prediction_index(session)
    features = []
    for asset in assets:
        p = _asset_payload(asset, predictions)
        lat, lng = p.get("latitude"), p.get("longitude")
        if lat is None or lng is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
            "properties": p,
        })
    return {"type": "FeatureCollection", "features": features, "total": len(features)}


@router.get("/gis/assets/bbox")
async def gis_bbox(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    limit: int = Query(1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_db),
):
    data = await gis_assets(limit=limit, asset_type=None, session=session)
    data["features"] = [f for f in data["features"] if min_lat <= f["geometry"]["coordinates"][1] <= max_lat and min_lng <= f["geometry"]["coordinates"][0] <= max_lng]
    data["total"] = len(data["features"])
    return data


@router.get("/gis/assets/{identifier}")
async def gis_asset(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    p = _asset_payload(asset, predictions)
    if p["latitude"] is None or p["longitude"] is None:
        raise HTTPException(status_code=404, detail="Asset coordinates unavailable")
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(p["longitude"]), float(p["latitude"])]}, "properties": p}


@router.get("/inspections")
async def inspections(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Inspection, Asset.asset_code).join(Asset, Asset.id == Inspection.asset_id).order_by(desc(Inspection.inspection_date)).limit(limit))).all()
    items = []
    for row, asset_code in rows:
        score = _value(row, "score", "condition_score", "inspection_score")
        items.append({
            "id": row.id,
            "asset_id": asset_code,
            "inspection_type": _value(row, "inspection_type", default="Inspection"),
            "inspection_date": _iso(_value(row, "inspection_date")),
            "inspector": _value(row, "inspector", "inspector_name"),
            "inspection_score": score,
            "condition_score": score,
            "condition": _value(row, "condition"),
            "notes": _value(row, "findings", "notes", "remarks"),
            "remarks": _value(row, "findings", "notes", "remarks"),
            "created_at": _iso(_value(row, "created_at", "inspection_date")),
        })
    return {"total": len(items), "items": items}


@router.get("/maintenance")
async def maintenance(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_db)):
    date_col = getattr(Maintenance, "maintenance_date", Maintenance.id)
    rows = (await session.execute(select(Maintenance, Asset.asset_code).join(Asset, Asset.id == Maintenance.asset_id).order_by(desc(date_col)).limit(limit))).all()
    items = []
    for row, asset_code in rows:
        items.append({
            "id": row.id,
            "asset_id": asset_code,
            "maintenance_type": _value(row, "maintenance_type", "action", default="Maintenance"),
            "description": _value(row, "description", "action"),
            "priority": _value(row, "priority"),
            "status": _value(row, "status", default="planned"),
            "cost": _value(row, "cost", "estimated_cost", "actual_cost"),
            "maintenance_date": _iso(_value(row, "maintenance_date")),
            "planned_start_date": _iso(_value(row, "planned_start_date", "maintenance_date")),
            "actual_completion_date": _iso(_value(row, "actual_completion_date")),
            "next_due": _iso(_value(row, "next_due")),
            "performed_by": _value(row, "performed_by", "assigned_contractor"),
            "created_at": _iso(_value(row, "created_at", "maintenance_date")),
        })
    return {"total": len(items), "items": items}


@router.get("/predictions")
async def predictions(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Prediction, Asset.asset_code, Asset.name).join(Asset, Asset.id == Prediction.asset_id).order_by(desc(Prediction.prediction_time)).limit(limit))).all()
    items = [{
        "id": row.id,
        "asset_id": asset_code,
        "asset_name": asset_name,
        "target": row.target,
        "value": row.value,
        "predicted_class": row.predicted_class,
        "confidence": row.confidence_score,
        "confidence_score": row.confidence_score,
        "lower_bound": row.lower_bound,
        "upper_bound": row.upper_bound,
        "model_version": row.model_version,
        "feature_version": row.feature_version,
        "status": row.status,
        "prediction_time": _iso(row.prediction_time),
        "predicted_at": _iso(row.prediction_time),
        "factors": row.factors,
    } for row, asset_code, asset_name in rows]
    return {"total": len(items), "items": items, "predictions": items}


@router.get("/predictions/summary")
async def prediction_summary(session: AsyncSession = Depends(get_db)):
    count = int(await session.scalar(select(func.count()).select_from(Prediction)) or 0)
    latest = await session.scalar(select(func.max(Prediction.prediction_time)))
    return {"total_predictions": count, "latest_prediction": _iso(latest)}


@router.get("/predictions/high-risk")
async def high_risk_predictions(limit: int = Query(50, ge=1, le=500), session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Prediction, Asset.asset_code, Asset.name).join(Asset, Asset.id == Prediction.asset_id).where(Prediction.target == "risk", Prediction.value >= 70).order_by(desc(Prediction.value)).limit(limit))).all()
    return [{"id": row.id, "asset_id": code, "asset_name": name, "risk_score": row.value, "risk_level": row.predicted_class or _risk_level(row.value), "confidence_score": row.confidence_score, "prediction_time": _iso(row.prediction_time)} for row, code, name in rows]


@router.get("/predictions/{identifier}")
async def prediction_for_asset(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    rows = (await session.scalars(select(Prediction).where(Prediction.asset_id == asset.id).order_by(desc(Prediction.prediction_time)))).all()
    latest = {}
    for row in rows:
        latest.setdefault(str(row.target).lower(), row)
    risk = latest.get("risk")
    health = latest.get("health")
    rul = latest.get("rul") or latest.get("remaining_life")
    return {
        "asset_id": asset.asset_code,
        "health_score": _value(health, "value"),
        "risk_score": _value(risk, "value"),
        "risk_level": _value(risk, "predicted_class", default=_risk_level(_value(risk, "value"))),
        "remaining_useful_life": _value(rul, "value"),
        "confidence_score": _value(risk, "confidence_score") or _value(health, "confidence_score"),
        "model_version": _value(risk, "model_version") or _value(health, "model_version"),
        "prediction_time": _iso(_value(risk, "prediction_time") or _value(health, "prediction_time")),
        "status": _value(risk, "status") or _value(health, "status") or "UNAVAILABLE",
    }


@router.get("/dashboard/overview")
async def dashboard_overview(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset))).all()
    predictions = await _prediction_index(session)
    payloads = [_asset_payload(a, predictions) for a in assets]
    by_type = Counter(str(a.get("asset_type") or "other").lower() for a in payloads)
    districts = Counter(str(a.get("district") or "Unknown") for a in payloads)
    risk_scores = [float(a["risk_score"]) for a in payloads if a.get("risk_score") is not None]
    health_scores = [float(a["health_score"]) for a in payloads if a.get("health_score") is not None]
    rul_values = [float(a["remaining_useful_life"]) for a in payloads if a.get("remaining_useful_life") is not None]
    high = [a for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) >= 70]
    medium = [a for a in payloads if a.get("risk_score") is not None and 40 <= float(a["risk_score"]) < 70]
    low = [a for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) < 40]
    top = sorted([a for a in payloads if a.get("risk_score") is not None], key=lambda a: float(a["risk_score"]), reverse=True)[:10]
    recent = sorted([a for a in payloads if a.get("prediction_time")], key=lambda a: a["prediction_time"], reverse=True)[:10]
    def avg(values):
        return round(sum(values) / len(values), 2) if values else 0.0
    return {
        "total_assets": len(payloads),
        "total_bridges": by_type.get("bridge", 0),
        "total_dams": by_type.get("dam", 0),
        "total_barrages": by_type.get("barrage", 0),
        "total_ports": by_type.get("port", 0),
        "total_roads": by_type.get("road", 0),
        "total_buildings": by_type.get("building", 0),
        "total_airports": by_type.get("airport", 0),
        "total_power_plants": by_type.get("powerplant", 0) + by_type.get("power_plant", 0),
        "high_risk_assets": len(high),
        "medium_risk_assets": len(medium),
        "low_risk_assets": len(low),
        "average_health_score": avg(health_scores),
        "average_risk_score": avg(risk_scores),
        "average_remaining_life": avg(rul_values),
        "district_distribution": [{"district": k, "count": v} for k, v in districts.most_common()],
        "asset_type_distribution": [{"asset_type": k, "count": v} for k, v in by_type.most_common()],
        "risk_distribution": [
            {"key": "low", "name": "Low Risk", "value": len(low)},
            {"key": "medium", "name": "Medium Risk", "value": len(medium)},
            {"key": "high", "name": "High Risk", "value": len(high)},
        ],
        "top_high_risk_assets": [{
            "id": a["asset_code"], "name": a["name"], "asset_type": a["asset_type"], "district": a["district"],
            "risk_score": a["risk_score"], "health_score": a["health_score"] or 0, "remaining_life": a["remaining_useful_life"] or 0,
        } for a in top],
        "recent_assessments": [{
            "assessment_id": f"pred-{a['asset_code']}", "assessment_name": f"{a['name']} assessment", "asset_id": a["asset_code"],
            "risk_level": a["risk_level"], "health_score": a["health_score"] or 0, "last_assessed": a["prediction_time"],
        } for a in recent],
    }


@router.get("/analytics/risk-analysis")
async def risk_analysis(session: AsyncSession = Depends(get_db)):
    overview = await dashboard_overview(session)
    return {"risk_distribution": overview["risk_distribution"], "top_high_risk_assets": overview["top_high_risk_assets"], "average_risk_score": overview["average_risk_score"]}


def _csv_response(rows, filename):
    stream = StringIO()
    if rows:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/reports/assets/csv")
async def report_assets_csv(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset).order_by(Asset.id))).all()
    predictions = await _prediction_index(session)
    return _csv_response([_asset_payload(a, predictions) for a in assets], "simras-assets.csv")


def _pdf_bytes(lines: list[str]) -> bytes:
    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    commands = ["BT", "/F1 12 Tf", "50 790 Td", "15 TL"]
    for line in lines:
        commands.append(f"({esc(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def _xlsx_bytes(rows: list[dict]) -> bytes:
    headers = list(rows[0].keys()) if rows else ["metric", "value"]
    def cell(ref: str, value) -> str:
        value = "" if value is None else str(value)
        return f'<c r="{ref}" t="inlineStr"><is><t>{html.escape(value)}</t></is></c>'
    def col_name(index: int) -> str:
        name = ""
        while index:
            index, rem = divmod(index - 1, 26)
            name = chr(65 + rem) + name
        return name
    xml_rows = []
    all_rows = [dict(zip(headers, headers))] + rows
    for r_idx, row in enumerate(all_rows, 1):
        cells = [cell(f"{col_name(c_idx)}{r_idx}", row.get(h, "")) for c_idx, h in enumerate(headers, 1)]
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>'
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="SIMRAS Summary" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return out.getvalue()


@router.get("/reports/summary/xlsx")
async def report_summary_download(session: AsyncSession = Depends(get_db)):
    overview = await dashboard_overview(session)
    rows = [{"metric": k, "value": v} for k, v in overview.items() if isinstance(v, (int, float, str))]
    return Response(_xlsx_bytes(rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="simras-summary.xlsx"'})


@router.get("/reports/asset/{identifier}/pdf")
async def report_asset_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    p = _asset_payload(asset, predictions)
    lines = [
        "SIMRAS Asset Report",
        f"Asset: {p['name']} ({p['asset_code']})",
        f"Type: {p['asset_type']}",
        f"District: {p['district']}",
        f"Identity: {p['identity_status']}",
        f"Health score: {p['health_score'] if p['health_score'] is not None else 'WITHHELD/UNAVAILABLE'}",
        f"Risk score: {p['risk_score'] if p['risk_score'] is not None else 'WITHHELD/UNAVAILABLE'}",
        f"Risk level: {p['risk_level']}",
        f"Prediction time: {p['prediction_time'] or 'N/A'}",
        "Decision-support output only; not an official engineering condition rating.",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-SIMRAS-report.pdf"'})

'@ | Set-Content ".\backend\app\api\routes\ui_compat.py" -Encoding UTF8

# Register compatibility router directly on FastAPI app.
$main = ".\backend\app\main.py"
$mainText = Get-Content $main -Raw
if ($mainText -notmatch "ui_compat_router") {
  Add-Content $main "`nfrom app.api.routes.ui_compat import router as ui_compat_router`napp.include_router(ui_compat_router, prefix=`"/api/v1`")`n"
}

# 12) Install UI dependencies used by src(1).zip while retaining existing Cesium/MapLibre packages.
Set-Location ".\frontend"
npm install --legacy-peer-deps @tanstack/react-query @tanstack/react-router @react-three/fiber three leaflet lucide-react recharts motion react-day-picker react-hook-form react-resizable-panels cmdk embla-carousel-react input-otp sonner vaul class-variance-authority clsx tailwind-merge tw-animate-css @radix-ui/react-accordion @radix-ui/react-alert-dialog @radix-ui/react-aspect-ratio @radix-ui/react-avatar @radix-ui/react-checkbox @radix-ui/react-collapsible @radix-ui/react-context-menu @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-hover-card @radix-ui/react-label @radix-ui/react-menubar @radix-ui/react-navigation-menu @radix-ui/react-popover @radix-ui/react-progress @radix-ui/react-radio-group @radix-ui/react-scroll-area @radix-ui/react-select @radix-ui/react-separator @radix-ui/react-slider @radix-ui/react-slot @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-toggle @radix-ui/react-toggle-group @radix-ui/react-tooltip
npm install -D --legacy-peer-deps tailwindcss @tailwindcss/postcss postcss @types/leaflet
if ($LASTEXITCODE -ne 0) { throw "NPM INSTALL FAILED" }

# 13) Build frontend and compile backend before touching running containers.
npm run build
if ($LASTEXITCODE -ne 0) { throw "FRONTEND BUILD FAILED - current working frontend backup is safe at $backup" }
Set-Location $repo
py -m py_compile ".\backend\app\api\routes\ui_compat.py" ".\backend\app\main.py"
if ($LASTEXITCODE -ne 0) { throw "BACKEND COMPILE FAILED" }

# 14) Rebuild and start only after both builds passed.
docker compose up -d --build --force-recreate backend frontend
Start-Sleep -Seconds 8

# 15) Smoke tests.
Write-Host "`n=== CONTAINERS ===" -ForegroundColor Cyan
docker compose ps
Write-Host "`n=== FRONTEND ===" -ForegroundColor Cyan
curl.exe -s -o NUL -w "HTTP %{http_code}`n" http://localhost:5173
Write-Host "`n=== DASHBOARD API ===" -ForegroundColor Cyan
curl.exe -s http://localhost:8000/api/v1/dashboard/overview | py -c "import sys,json; d=json.load(sys.stdin); print('assets=',d.get('total_assets'),' high=',d.get('high_risk_assets'),' avg_health=',d.get('average_health_score'))"
Write-Host "`n=== GIS API ===" -ForegroundColor Cyan
curl.exe -s "http://localhost:8000/api/v1/gis/assets?limit=3" | py -c "import sys,json; d=json.load(sys.stdin); print('GIS features=',len(d.get('features',[])))"
Write-Host "`n=== INSPECTIONS / MAINTENANCE ===" -ForegroundColor Cyan
curl.exe -s "http://localhost:8000/api/v1/inspections?limit=3" | py -c "import sys,json; d=json.load(sys.stdin); print('inspections=',len(d.get('items',[])))"
curl.exe -s "http://localhost:8000/api/v1/maintenance?limit=3" | py -c "import sys,json; d=json.load(sys.stdin); print('maintenance=',len(d.get('items',[])))"
Write-Host "`n=== EXISTING REAL TWIN API ===" -ForegroundColor Cyan
curl.exe -s -o NUL -w "HTTP %{http_code}`n" http://localhost:8000/api/v1/assets/AP_DAM_00001/twin

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SIMRAS NEW UI + EXISTING PROJECT LINKED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Process "http://localhost:5173"
