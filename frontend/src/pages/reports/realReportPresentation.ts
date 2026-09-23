const blockedExact = new Set([
  "",
  "N/A",
  "NA",
  "NULL",
  "NONE",
  "UNKNOWN",
  "NOT AVAILABLE",
  "NOT_AVAILABLE",
  "NOT VERIFIED",
  "NOT_VERIFIED",
  "WITHHELD",
  "MISSING",
  "UNAVAILABLE",
]);

function normalise(value: string) {
  return value.trim().toUpperCase().replace(/-/g, " ").replace(/\s+/g, " ");
}

export function isDisplayableReportValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "boolean" || typeof value === "number") return true;
  if (typeof value === "string") {
    const text = normalise(value);
    const canonical = text.replace(/ /g, "_");
    if (blockedExact.has(text) || blockedExact.has(canonical)) return false;
    return !canonical.startsWith("INSUFFICIENT") && !canonical.startsWith("WITHHELD_");
  }
  return false;
}

export function labelForReportKey(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function displayableReportEntries(mapping: Record<string, unknown> | null | undefined): [string, string][] {
  if (!mapping) return [];
  return Object.entries(mapping)
    .filter(([, value]) => isDisplayableReportValue(value))
    .map(([key, value]) => [labelForReportKey(key), typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)]);
}
