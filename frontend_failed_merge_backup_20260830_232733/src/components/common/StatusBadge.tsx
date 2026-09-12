import { cn } from "../../lib/utils";
import type { HealthStatus, RiskLevel } from "../../types";

const healthMap: Record<HealthStatus, { label: string; cls: string }> = {
  healthy: { label: "Healthy", cls: "border-success/30 bg-success/10 text-success" },
  warning: { label: "Warning", cls: "border-warning/40 bg-warning/12 text-warning" },
  critical: { label: "Critical", cls: "border-danger/30 bg-danger/10 text-danger" },
};

const riskMap: Record<RiskLevel, { label: string; cls: string }> = {
  low: { label: "Low Risk", cls: "border-success/30 bg-success/10 text-success" },
  medium: { label: "Medium Risk", cls: "border-warning/40 bg-warning/12 text-warning" },
  high: { label: "High Risk", cls: "border-danger/30 bg-danger/10 text-danger" },
};

const base =
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap";

export function StatusBadge({ status, className }: { status: HealthStatus; className?: string }) {
  const item = healthMap[status];
  return (
    <span className={cn(base, item.cls, className)}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {item.label}
    </span>
  );
}

export function RiskBadge({ risk, className }: { risk: RiskLevel; className?: string }) {
  const item = riskMap[risk];
  return <span className={cn(base, item.cls, className)}>{item.label}</span>;
}
