import type { LucideIcon } from "lucide-react";
import { cn } from "../../lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  delta?: string;
  tone?: "default" | "success" | "warning" | "danger" | "accent";
  className?: string;
}

const toneMap = {
  default: "text-primary bg-primary/8 border-primary/20",
  success: "text-success bg-success/10 border-success/25",
  warning: "text-warning bg-warning/12 border-warning/30",
  danger: "text-danger bg-danger/10 border-danger/25",
  accent: "text-accent bg-accent/10 border-accent/25",
} as const;

export function StatCard({ label, value, icon: Icon, delta, tone = "default", className }: StatCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-4 shadow-panel sm:p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="eyebrow min-w-0 text-muted-foreground">{label}</p>
        {Icon && (
          <span className={cn("grid size-8 shrink-0 place-items-center rounded-md border", toneMap[tone])}>
            <Icon className="size-4" aria-hidden="true" />
          </span>
        )}
      </div>
      <p className="mt-3 font-display text-3xl font-bold tabular-nums tracking-tight">{value}</p>
      {delta && <p className="mt-1 text-xs text-muted-foreground">{delta}</p>}
    </div>
  );
}
