import type { AssetSummary } from "../types/twin";

type Props = {
  assets: AssetSummary[];
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
};

function AssetRow({
  asset,
  selectedCode,
  onSelect,
}: {
  asset: AssetSummary;
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
}) {
  return (
    <button
      type="button"
      className={`simple-asset-row ${
        selectedCode === asset.asset_code ? "selected" : ""
      }`}
      onClick={() => onSelect(asset)}
    >
      <strong className="simple-asset-name">
        {asset.name}
      </strong>

      <div className="simple-asset-meta">
        <span>{asset.asset_type}</span>
        <span>{asset.district ?? "District unavailable"}</span>
      </div>
    </button>
  );
}

function Section({
  title,
  items,
  selectedCode,
  onSelect,
}: {
  title: string;
  items: AssetSummary[];
  selectedCode?: string;
  onSelect: (asset: AssetSummary) => void;
}) {
  if (items.length === 0) return null;

  return (
    <section className="simple-asset-section">
      <div className="simple-section-title">
        {title}
      </div>

      <div className="simple-asset-items">
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
  // Keep the existing best-twin-first ordering.
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
    <div className="simple-asset-list">
      <Section
        title="Best digital twins"
        items={best}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />

      <Section
        title="Developing twins"
        items={improving}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />

      <Section
        title="Other assets"
        items={basic}
        selectedCode={selectedCode}
        onSelect={onSelect}
      />
    </div>
  );
}
