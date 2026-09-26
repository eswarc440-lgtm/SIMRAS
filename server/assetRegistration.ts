const ASSET_TYPES = new Set(["dam", "barrage", "bridge", "airport", "temple"]);

export interface AssetRegistrationInput {
  asset_code?: unknown;
  name?: unknown;
  type?: unknown;
  asset_type?: unknown;
  category?: unknown;
  subtype?: unknown;
  district?: unknown;
  state?: unknown;
  latitude?: unknown;
  longitude?: unknown;
  coordinates?: { latitude?: unknown; longitude?: unknown };
  dimensions?: Record<string, unknown>;
  specifications?: Record<string, unknown>;
  built_year?: unknown;
  material?: unknown;
  dimension_authority?: unknown;
  condition?: unknown;
  health_score?: unknown;
  risk_score?: unknown;
  priority?: unknown;
  source_url?: unknown;
}

function requiredText(value: unknown, message: string) {
  const text = String(value ?? "").trim();
  if (!text) throw new Error(message);
  return text;
}

function optionalNumber(value: unknown, field: string) {
  if (value === undefined || value === null || value === "") return undefined;
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${field} must be a valid number`);
  return number;
}

export function normalizeAssetRegistrationPayload(input: AssetRegistrationInput) {
  const name = requiredText(input.name, "Official asset name is required");
  const assetType = requiredText(input.asset_type ?? input.type, "Asset type is required").toLowerCase();
  if (!ASSET_TYPES.has(assetType)) throw new Error("Asset type is invalid");

  const latitude = optionalNumber(input.latitude ?? input.coordinates?.latitude, "Latitude");
  const longitude = optionalNumber(input.longitude ?? input.coordinates?.longitude, "Longitude");
  if (latitude === undefined || longitude === undefined) throw new Error("Latitude and longitude are required");
  if (latitude < 12 || latitude > 20 || longitude < 76 || longitude > 85) {
    throw new Error("Coordinates must be within Andhra Pradesh bounds");
  }

  const healthScore = optionalNumber(input.health_score, "Health score");
  const riskScore = optionalNumber(input.risk_score, "Risk score");
  for (const [label, value] of [["Health score", healthScore], ["Risk score", riskScore]] as const) {
    if (value !== undefined && (value < 0 || value > 100)) throw new Error(`${label} must be between 0 and 100`);
  }

  const specifications = input.dimensions ?? input.specifications ?? {};
  return {
    asset_code: String(input.asset_code ?? "").trim() || undefined,
    name,
    asset_type: assetType,
    subtype: String(input.subtype ?? `standard_${assetType}`),
    district: requiredText(input.district, "District is required"),
    state: String(input.state ?? "Andhra Pradesh"),
    latitude,
    longitude,
    dimensions: { ...specifications },
    built_year: optionalNumber(input.built_year ?? specifications.built_year, "Built year"),
    material: String(input.material ?? specifications.material ?? ""),
    dimension_authority: String(input.dimension_authority ?? specifications.dimension_authority ?? "Officer registration"),
    condition: String(input.condition ?? "Not assessed"),
    health_score: healthScore,
    risk_score: riskScore,
    priority: optionalNumber(input.priority, "Priority"),
    source_url: input.source_url ? String(input.source_url) : undefined,
  };
}
