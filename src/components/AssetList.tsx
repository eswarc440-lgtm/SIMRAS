import type { AssetSummary } from "../types/twin";
import { riskColor } from "../utils";
import { StatusPill } from "./StatusPill";

interface AssetListProps {
  assets: AssetSummary[];
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
}

export function AssetList({ assets, selectedCode, onSelect }: AssetListProps) {
  return (
    <div className="asset-list">
      {assets.map((asset) => (
        <button
          className={`asset-row ${selectedCode === asset.asset_code ? "active" : ""}`}
          key={asset.asset_code}
          onClick={() => onSelect(asset)}
          type="button"
        >
          <span className="risk-dot" style={{ background: riskColor(asset.risk_level) }} />
          <span className="asset-copy">
            <strong>{asset.name}</strong>
            <small>{asset.district ?? "District unavailable"} · {asset.asset_type}</small>
          </span>
          <span className="asset-score">
            {asset.risk_score?.toFixed(0) ?? "—"}
            <StatusPill
              label={asset.identity_status}
              tone={asset.identity_status === "VERIFIED" ? "good" : "warn"}
            />
          </span>
        </button>
      ))}
    </div>
  );
}

