import type { CSSProperties } from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  detail: string;
  accent?: string;
}

export function KpiCard({ label, value, detail, accent = "#6dd5ed" }: KpiCardProps) {
  return (
    <article className="kpi-card" style={{ "--accent": accent } as CSSProperties}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}
