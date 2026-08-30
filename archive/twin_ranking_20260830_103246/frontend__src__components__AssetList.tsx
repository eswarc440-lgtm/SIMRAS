import type { AssetSummary } from "../types/twin";

type Props = {
  assets: AssetSummary[];
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
};

function qualityColour(asset: AssetSummary): string {
  switch (asset.twin_quality) {
    case "EXCELLENT":
      return "#37d3a2";
    case "READY":
      return "#38bdf8";
    case "PARTIAL":
      return "#f7c948";
    default:
      return "#94a3b8";
  }
}

function AssetRow({
  asset,
  selectedCode,
  onSelect,
}: {
  asset: AssetSummary;
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
}) {
  const colour = qualityColour(asset);

  return (
    <button
      type="button"
      className={`ranked-asset-row ${
        selectedCode === asset.asset_code ? "selected" : ""
      }`}
      onClick={() => onSelect(asset)}
    >
      <div className="ranked-asset-topline">
        <strong>{asset.name}</strong>

        <span
          className="twin-quality-badge"
          style={{
            color: colour,
            borderColor: `${colour}66`,
          }}
        >
          {asset.twin_quality ?? "BASIC"}
        </span>
      </div>

      <div className="ranked-asset-meta">
        <span>{asset.asset_type}</span>
        <span>{asset.district ?? "District unavailable"}</span>
      </div>

      <div className="ranked-twin-meta">
        <span>
          <b>{asset.twin_fidelity ?? "L0"}</b>
          {" Â· "}
          {asset.twin_source_backed ? "source-backed" : "illustrative"}
        </span>

        <span>
          {asset.twin_dimension_count ?? 0} geometry fields
        </span>
      </div>

      <div className="ranked-score-row">
        <span>
          Twin quality
          <b>{asset.twin_quality_score ?? 0}/100</b>
        </span>

        <span>
          Risk
          <b>
            {asset.risk_score != null
              ? asset.risk_score.toFixed(0)
              : "â€”"}
          </b>
        </span>
      </div>

      <small className="ranked-quality-description">
        {asset.twin_quality_label ??
          "Source-backed geometry is incomplete"}
      </small>
    </button>
  );
}

function Section({
  title,
  subtitle,
  items,
  selectedCode,
  onSelect,
}: {
  title: string;
  subtitle: string;
  items: AssetSummary[];
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
}) {
  if (items.length === 0) return null;

  return (
    <section className="ranked-asset-section">
      <header className="ranked-section-header">
        <div>
          <strong>{title}</strong>
          <small>{subtitle}</small>
        </div>
        <span>{items.length}</span>
      </header>

      <div className="ranked-asset-items">
        {items.map((asset) => (
          <AssetRow
            key={asset.asset_code}
            asset={asset}
            selectedCode={selectedCode}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}

export function AssetList({
  assets,
  selectedCode,
  onSelect,
}: Props) {
  const ranked = [...assets].sort((a, b) => {
    const quality =
      (b.twin_quality_score ?? 0) -
      (a.twin_quality_score ?? 0);

    if (quality !== 0) return quality;

    return (
      (b.risk_score ?? -1) -
      (a.risk_score ?? -1)
    );
  });

  const best = ranked.filter(
    (asset) => asset.twin_group === "BEST",
  );

  const improving = ranked.filter(
    (asset) => asset.twin_group === "IMPROVING",
  );

  const basic = ranked.filter(
    (asset) =>
      !asset.twin_group ||
      asset.twin_group === "BASIC",
  );

  return (
    <div className="ranked-asset-list">
      <Section
        title="Best digital twins"
        subtitle="Source-backed and structured â€” open these first"
        items={best}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />

      <Section
        title="Developing twins"
        subtitle="Useful geometry, but more verified dimensions are needed"
        items={improving}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />

      <Section
        title="Illustrative / incomplete"
        subtitle="Low-fidelity assets stay below until better source geometry is linked"
        items={basic}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />
    </div>
  );
}