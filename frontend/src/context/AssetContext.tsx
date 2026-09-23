import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { AssetSummary, TwinResponse } from "../types/twin";
import type { EvidenceStateResponse } from "../types/evidence";
import { api } from "../services/simrasTwinApi";

interface AssetContextType {
  assets: AssetSummary[];
  selected: AssetSummary | undefined;
  selectedCode: string | undefined;
  twin: TwinResponse | undefined;
  evidenceState: EvidenceStateResponse | undefined;
  loading: boolean;
  assetLoading: boolean;
  error: string | undefined;
  setSelectedCode: (code: string) => void;
  selectAsset: (asset: AssetSummary) => void;
  refreshAsset: () => void;
}

const AssetContext = createContext<AssetContextType | undefined>(undefined);

export function AssetProvider({ children }: { children: React.ReactNode }) {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [selected, setSelected] = useState<AssetSummary>();
  const [selectedCode, setSelectedCodeState] = useState<string>();
  const [twin, setTwin] = useState<TwinResponse>();
  const [evidenceState, setEvidenceState] = useState<EvidenceStateResponse>();
  const [loading, setLoading] = useState(true);
  const [assetLoading, setAssetLoading] = useState(false);
  const [error, setError] = useState<string>();

  // Fetch all assets on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.assets({ limit: 1000, offset: 0 })
      .then((res) => {
        if (cancelled) return;
        const ranked = [...res.items].sort(
          (a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1)
        );
        setAssets(ranked);
        if (ranked.length > 0 && !selectedCode) {
          const defaultCode = import.meta.env.VITE_DEFAULT_ASSET_ID || "AP_DAM_00001";
          const initial = ranked.find((a) => a.asset_code === defaultCode) ?? ranked[0];
          setSelected(initial);
          setSelectedCodeState(initial.asset_code);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch selected asset twin & evidence whenever selectedCode changes
  const fetchAssetDetails = useCallback((code: string) => {
    let cancelled = false;
    // PURGE STALE DATA IMMEDIATELY
    setTwin(undefined);
    setEvidenceState(undefined);
    setAssetLoading(true);

    Promise.allSettled([api.twin(code), api.state(code)]).then(([twinRes, stateRes]) => {
      if (cancelled) return;
      if (twinRes.status === "fulfilled" && twinRes.value.asset?.asset_code === code) {
        setTwin(twinRes.value);
      }
      if (stateRes.status === "fulfilled") {
        setEvidenceState(stateRes.value);
      }
      setAssetLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedCode) return;
    const cancel = fetchAssetDetails(selectedCode);
    return cancel;
  }, [selectedCode, fetchAssetDetails]);

  const selectAsset = useCallback((asset: AssetSummary) => {
    setSelected(asset);
    setSelectedCodeState(asset.asset_code);
  }, []);

  const setSelectedCode = useCallback((code: string) => {
    setSelectedCodeState(code);
    const found = assets.find((a) => a.asset_code === code);
    if (found) setSelected(found);
  }, [assets]);

  const refreshAsset = useCallback(() => {
    if (selectedCode) fetchAssetDetails(selectedCode);
  }, [selectedCode, fetchAssetDetails]);

  return (
    <AssetContext.Provider
      value={{
        assets,
        selected,
        selectedCode,
        twin,
        evidenceState,
        loading,
        assetLoading,
        error,
        setSelectedCode,
        selectAsset,
        refreshAsset,
      }}
    >
      {children}
    </AssetContext.Provider>
  );
}

export function useSelectedAsset() {
  const ctx = useContext(AssetContext);
  if (!ctx) throw new Error("useSelectedAsset must be used within AssetProvider");
  return ctx;
}
