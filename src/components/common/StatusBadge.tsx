import React from "react";

export type StatusType =
  | "VERIFIED"
  | "APPROVED"
  | "PENDING"
  | "PENDING_REVIEW"
  | "SCHEDULED"
  | "DUE_SOON"
  | "OVERDUE"
  | "IN_PROGRESS"
  | "UNDER_REVIEW"
  | "COMPLETED"
  | "HIGH_RISK"
  | "MEDIUM_RISK"
  | "LOW_RISK"
  | "REVISION_REQUIRED"
  | "REJECTED"
  | "CRITICAL"
  | "HEALTHY"
  | "ACTIVE"
  | string;

interface StatusBadgeProps {
  status: StatusType;
  size?: "sm" | "md" | "lg";
  className?: string;
  labelOverride?: string;
}

export function StatusBadge({ status, size = "sm", className = "", labelOverride }: StatusBadgeProps) {
  const norm = (status || "").toUpperCase().replace(/\s+/g, "_");

  let text = labelOverride || norm.replace(/_/g, " ");
  let bg = "bg-slate-100";
  let textCol = "text-slate-700";
  let border = "border-slate-200";
  let dot = "bg-slate-400";

  switch (norm) {
    case "VERIFIED":
    case "APPROVED":
    case "COMPLETED":
    case "HEALTHY":
    case "LOW_RISK":
    case "LOW":
    case "ACTIVE":
      bg = "bg-emerald-50";
      textCol = "text-emerald-800";
      border = "border-emerald-200";
      dot = "bg-emerald-500";
      if (!labelOverride) {
        if (norm === "LOW_RISK" || norm === "LOW") text = "Low Risk";
        else if (norm === "VERIFIED") text = "Verified";
        else if (norm === "APPROVED") text = "Approved";
        else if (norm === "COMPLETED") text = "Completed";
        else if (norm === "HEALTHY") text = "Healthy";
      }
      break;

    case "SCHEDULED":
      bg = "bg-blue-50";
      textCol = "text-blue-800";
      border = "border-blue-200";
      dot = "bg-blue-500";
      if (!labelOverride) text = "Scheduled";
      break;

    case "IN_PROGRESS":
      bg = "bg-sky-50";
      textCol = "text-sky-800";
      border = "border-sky-200";
      dot = "bg-sky-500";
      if (!labelOverride) text = "In Progress";
      break;

    case "DUE_SOON":
    case "UNDER_REVIEW":
    case "PENDING":
    case "PENDING_REVIEW":
    case "MEDIUM_RISK":
    case "MEDIUM":
    case "MODERATE_RISK":
    case "MODERATE":
      bg = "bg-amber-50";
      textCol = "text-amber-800";
      border = "border-amber-200";
      dot = "bg-amber-500";
      if (!labelOverride) {
        if (norm === "DUE_SOON") text = "Due Soon";
        else if (norm === "UNDER_REVIEW") text = "Under Review";
        else if (norm === "PENDING_REVIEW" || norm === "PENDING") text = "Pending Review";
        else if (norm === "MEDIUM_RISK" || norm === "MEDIUM") text = "Medium Risk";
      }
      break;

    case "OVERDUE":
    case "HIGH_RISK":
    case "HIGH":
    case "CRITICAL":
    case "REJECTED":
      bg = "bg-red-50";
      textCol = "text-red-800";
      border = "border-red-200";
      dot = "bg-red-500";
      if (!labelOverride) {
        if (norm === "OVERDUE") text = "Overdue";
        else if (norm === "HIGH_RISK" || norm === "HIGH") text = "High Risk";
        else if (norm === "CRITICAL") text = "Critical Risk";
        else if (norm === "REJECTED") text = "Rejected";
      }
      break;

    case "REVISION_REQUIRED":
      bg = "bg-orange-50";
      textCol = "text-orange-800";
      border = "border-orange-200";
      dot = "bg-orange-500";
      if (!labelOverride) text = "Revision Required";
      break;

    default:
      break;
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[11px]",
    md: "px-2.5 py-1 text-xs",
    lg: "px-3 py-1.5 text-sm",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-md border ${bg} ${textCol} ${border} ${sizeClasses[size]} tracking-tight shrink-0 ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
      <span className="truncate">{text}</span>
    </span>
  );
}
