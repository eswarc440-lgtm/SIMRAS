interface StatusPillProps {
  label: string;
  tone?: "good" | "warn" | "danger" | "neutral";
}

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{label.replaceAll("_", " ")}</span>;
}

