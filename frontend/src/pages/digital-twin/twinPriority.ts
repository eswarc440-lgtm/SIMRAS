type TwinRankable = {
  asset_code: string;
  name: string;
  twin_quality_score?: number;
  fidelity_level?: string;
  twin_fidelity?: string;
  twin_group?: string;
};

const SHOWCASE_PRIORITY = new Map<string, number>([
  ["AP_DAM_00002", 0],
  ["AP_DAM_00001", 1],
  ["AP_BAR_WRIS_B00131", 2],
  ["AP_DAM_NWDP_AP01VH0059", 3],
  ["AP_DAM_WRIS_AP01HH0062", 4],
  ["AP_AIR_VOBZ", 5],
  ["AP_AIR_VOTP", 6],
  ["AP_TEMPLE_TTD_0001", 7],
]);

const FIDELITY_SCORE: Record<string, number> = {
  L3: 3000,
  L2: 2000,
  L1: 1000,
  L0: 0,
};

function normalizedFidelity(item: TwinRankable) {
  const raw = String(item.fidelity_level ?? item.twin_fidelity ?? "").toUpperCase();
  const match = raw.match(/L[0-3]/);
  if (match) return match[0];
  if (item.twin_group === "BEST") return "L2";
  return "L0";
}

function evidencePriority(item: TwinRankable) {
  const showcase = SHOWCASE_PRIORITY.get(item.asset_code);
  if (showcase !== undefined) return 10000 - showcase;
  return FIDELITY_SCORE[normalizedFidelity(item)] + (item.twin_quality_score ?? 0);
}

export function rankDigitalTwins<T extends TwinRankable>(items: readonly T[]): T[] {
  return [...items].sort((left, right) => {
    const evidenceDifference = evidencePriority(right) - evidencePriority(left);
    if (evidenceDifference !== 0) return evidenceDifference;
    return left.name.localeCompare(right.name);
  });
}

export function applyDigitalTwinPriorityScores<T extends TwinRankable>(items: readonly T[]): T[] {
  return items.map((item) => ({
    ...item,
    twin_quality_score: evidencePriority(item),
  }));
}
