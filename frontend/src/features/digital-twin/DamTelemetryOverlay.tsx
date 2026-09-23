import type { TwinResponse } from "../../types/twin";

type EnvRow = {
  value?: number | null;
  unit?: string | null;
  observed_at?: string | null;
  source_name?: string | null;
  confidence?: number | null;
  is_estimated?: boolean | null;
};

type EnvMap = Record<string, EnvRow | undefined>;

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function envRow(twin: TwinResponse, ...keys: string[]): EnvRow | null {
  const env =
    ((twin as unknown as { environment?: EnvMap }).environment ?? {}) as EnvMap;

  for (const key of keys) {
    const row = env[key];
    if (row && finite(row.value) != null) return row;
  }
  return null;
}

function dimension(twin: TwinResponse, ...keys: string[]): number | null {
  const dims = (twin.twin.dimensions ?? {}) as Record<string, unknown>;

  for (const key of keys) {
    const value = finite(dims[key]);
    if (value != null && value > 0) return value;
  }
  return null;
}

function formatValue(value: number | null, unit: string, digits = 1): string {
  if (value == null) return "N/A";
  return `${value.toFixed(digits)} ${unit}`;
}

export function DamTelemetryOverlay({ twin }: { twin: TwinResponse }) {
  const type = String(twin.asset.asset_type ?? "").toLowerCase();
  if (type !== "dam" && type !== "barrage") return null;

  const temperature = envRow(twin, "temperature_2m", "temperature");
  const level = envRow(twin, "reservoir_level", "water_level");
  const storage = envRow(twin, "reservoir_storage", "storage");

  const capacity = dimension(
    twin,
    "gross_storage_mcm",
    "storage_capacity_mcm",
    "reservoir_capacity_mcm",
    "capacity_mcm",
    "live_storage_mcm",
  );

  const storageValue = finite(storage?.value);
  const storagePct =
    storageValue != null && capacity != null && capacity > 0
      ? Math.max(0, (storageValue / capacity) * 100)
      : null;

  const timestamps = [temperature, level, storage]
    .map((row) => row?.observed_at)
    .filter((value): value is string => Boolean(value))
    .sort();

  const newestTimestamp = timestamps.length
    ? timestamps[timestamps.length - 1]
    : null;

  return (
    <aside className="dam-telemetry-overlay" aria-label="Dam telemetry display">
      <div className="dam-telemetry-header">
        <div>
          <span className="dam-telemetry-kicker">DIGITAL SCREEN</span>
          <strong>Reservoir telemetry</strong>
        </div>
        <span className="dam-telemetry-status">SOURCE BACKED</span>
      </div>

      <div className="dam-telemetry-grid">
        <div className="dam-telemetry-cell">
          <span>Temperature</span>
          <strong>{formatValue(finite(temperature?.value), "°C")}</strong>
          <small>{temperature?.source_name ?? "Current environment"}</small>
        </div>

        <div className="dam-telemetry-cell">
          <span>Water level</span>
          <strong>{formatValue(finite(level?.value), level?.unit || "m")}</strong>
          <small>{level?.source_name ?? "Reservoir observation"}</small>
        </div>

        <div className="dam-telemetry-cell">
          <span>Current storage</span>
          <strong>{formatValue(storageValue, storage?.unit || "MCM")}</strong>
          <small>{storage?.source_name ?? "Reservoir observation"}</small>
        </div>

        <div className="dam-telemetry-cell">
          <span>Reservoir capacity</span>
          <strong>{formatValue(capacity, "MCM")}</strong>
          <small>Published / linked asset dimension</small>
        </div>
      </div>

      <div className="dam-telemetry-footer">
        <div>
          <span>Storage utilisation</span>
          <strong>{storagePct == null ? "N/A" : `${storagePct.toFixed(1)}%`}</strong>
        </div>
        <div>
          <span>Updated</span>
          <strong>
            {newestTimestamp
              ? new Date(newestTimestamp).toLocaleString()
              : "No timestamp"}
          </strong>
        </div>
      </div>
    </aside>
  );
}
