import type { RiskLevel } from "./types/twin";

export function riskColor(level?: RiskLevel | null): string {
  if (level === "HIGH") return "#ff5b62";
  if (level === "MEDIUM") return "#f3b647";
  return "#37d3a2";
}

export function formatValue(value: number | string | null, unit?: string | null): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const rendered = typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : value;
  return `${rendered}${unit ? ` ${unit}` : ""}`;
}

