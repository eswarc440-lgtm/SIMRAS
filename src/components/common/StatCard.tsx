import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: {
    direction: "up" | "down" | "neutral";
    label: string;
  };
  icon?: LucideIcon;
  variant?: "default" | "primary" | "warning" | "danger" | "success";
  className?: string;
  onClick?: () => void;
}

export function StatCard({
  label,
  value,
  subtext,
  trend,
  icon: Icon,
  variant = "default",
  className = "",
  onClick,
}: StatCardProps) {
  const borderVariants = {
    default: "border-[#D8E2EA] hover:border-slate-300",
    primary: "border-blue-200 bg-blue-50/20",
    warning: "border-amber-200 bg-amber-50/20",
    danger: "border-red-200 bg-red-50/20",
    success: "border-emerald-200 bg-emerald-50/20",
  };

  const textVariants = {
    default: "text-[#0F172A]",
    primary: "text-[#1268A8]",
    warning: "text-amber-700",
    danger: "text-red-700",
    success: "text-emerald-700",
  };

  const iconBg = {
    default: "bg-slate-100 text-slate-600",
    primary: "bg-blue-100 text-[#1268A8]",
    warning: "bg-amber-100 text-amber-700",
    danger: "bg-red-100 text-red-700",
    success: "bg-emerald-100 text-emerald-700",
  };

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-lg border p-4 shadow-sm transition-all ${
        onClick ? "cursor-pointer hover:shadow-md" : ""
      } ${borderVariants[variant]} ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {label}
        </span>
        {Icon && (
          <div className={`p-1.5 rounded-md ${iconBg[variant]}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className={`text-2xl sm:text-3xl font-bold tracking-tight ${textVariants[variant]}`}>
          {value}
        </span>
        {trend && (
          <span
            className={`text-xs font-medium ${
              trend.direction === "up"
                ? "text-emerald-600"
                : trend.direction === "down"
                ? "text-red-600"
                : "text-slate-500"
            }`}
          >
            {trend.label}
          </span>
        )}
      </div>

      {subtext && <p className="mt-1 text-xs text-slate-500 truncate">{subtext}</p>}
    </div>
  );
}
