import { useCallback, useEffect, useMemo, useState } from "react";
import type { AssetSummary } from "../types/twin";

export type AssetView =
  | "gis"
  | "digital-twin"
  | "reports"
  | "inspections"
  | "maintenance";

export function readSelectedAssetCode(search: string): string | null {
  return new URLSearchParams(search).get("asset");
}

export function resolveSelectedAssetCode(
  assets: AssetSummary[],
  requested: string | null,
): string | null {
  if (requested && assets.some((asset) => asset.asset_code === requested)) {
    return requested;
  }
  return assets[0]?.asset_code ?? null;
}

export function buildAssetUrl(
  view: AssetView | undefined,
  assetCode: string,
  currentUrl = "/",
): string {
  const url = new URL(currentUrl, "https://simras.local");
  if (view) url.pathname = `/${view}`;
  url.searchParams.set("asset", assetCode);
  return `${url.pathname}${url.search}`;
}

export function useSelectedAsset(assets: AssetSummary[]) {
  const initialRequest = useMemo(
    () =>
      typeof window === "undefined"
        ? null
        : readSelectedAssetCode(window.location.search),
    [],
  );
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(
    initialRequest,
  );

  useEffect(() => {
    const resolved = resolveSelectedAssetCode(assets, selectedAssetCode);
    if (resolved !== selectedAssetCode) setSelectedAssetCode(resolved);
    if (resolved && typeof window !== "undefined") {
      const current = `${window.location.pathname}${window.location.search}`;
      window.history.replaceState({}, "", buildAssetUrl(undefined, resolved, current));
    }
  }, [assets, selectedAssetCode]);

  const selectedAsset = useMemo(
    () => assets.find((asset) => asset.asset_code === selectedAssetCode),
    [assets, selectedAssetCode],
  );

  const selectAsset = useCallback(
    (assetOrCode: AssetSummary | string, view?: AssetView) => {
      const code =
        typeof assetOrCode === "string" ? assetOrCode : assetOrCode.asset_code;
      if (!assets.some((asset) => asset.asset_code === code)) return;
      setSelectedAssetCode(code);
      if (typeof window !== "undefined") {
        const current = `${window.location.pathname}${window.location.search}`;
        window.history.replaceState({}, "", buildAssetUrl(view, code, current));
      }
    },
    [assets],
  );

  return { selectedAssetCode, selectedAsset, selectAsset, buildAssetUrl };
}
