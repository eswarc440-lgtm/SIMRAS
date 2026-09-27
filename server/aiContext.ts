import { db } from "./db";

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export function trimConversationHistory(history: ConversationMessage[] = []) {
  return (Array.isArray(history) ? history : []).filter((message) => message &&
    (message.role === "user" || message.role === "assistant") && typeof message.content === "string" && !!message.content.trim(),
  ).slice(-8);
}

export class AmbiguousAssetError extends Error {
  constructor(public choices: {asset_code:string;name:string;district?:string}[]) { super('Multiple assets match. Select an asset code.'); }
}

// Common aliases for major assets
const ASSET_ALIASES: Record<string, string[]> = {
  'prakasam barrage': ['prakasam', 'prakasha barrage', 'prakasam bridge', 'prakash marriage', 'buckingham canal'],
  'srisailam': ['srisailam project', 'nsrsp', 'n.s.r.s.p', 'srisailam dam'],
  'nagarjuna sagar': ['nagarjuna sagar dam', 'nagarjuna sagar project'],
  'godavari arch bridge': ['godavari bridge', 'godavari arch'],
  'kanaka durga flyover': ['kanaka durga', 'kanaka durga bridge', 'vijayawada flyover'],
  'vijayawada airport': ['vijayawada air', 'airport vijayawada'],
  'visakhapatnam airport': ['vizag airport', 'visakhapatnam air'],
};

function normalizeAssetName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '') // Remove special characters
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
}

function calculateSimilarity(str1: string, str2: string): number {
  const s1 = normalizeAssetName(str1);
  const s2 = normalizeAssetName(str2);
  
  if (s1 === s2) return 1.0;
  if (s1.includes(s2) || s2.includes(s1)) return 0.8;
  
  // Simple token overlap
  const tokens1 = s1.split(' ');
  const tokens2 = s2.split(' ');
  const intersection = tokens1.filter(t => tokens2.includes(t));
  const union = [...new Set([...tokens1, ...tokens2])];
  
  return intersection.length / union.length;
}

export function resolveAsset<T extends {asset_code:string;name:string;district?:string}>(
  assets:T[],
  selectedCode:string,
  question:string
):T {
  const normalize = (value: unknown) =>
    String(value ?? "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  // Common speech / typing variants that occur in SIMRAS queries.
  // This is only for NAME RESOLUTION. It never changes stored asset data.
  const canonicalize = (value: unknown) =>
    normalize(value)
      .replace(/\bprakasham\b/g, "prakasam")
      .replace(/\bprakash\b/g, "prakasam")
      .replace(/\bprakasam\b/g, "prakasam")
      .replace(/\bmarriage\b/g, "barrage")
      .replace(/\bbarrag\b/g, "barrage")
      .replace(/\bfly over\b/g, "flyover")
      .replace(/\s+/g, " ")
      .trim();

  const choices = (rows:T[]) =>
    rows.map(({asset_code,name,district}) => ({
      asset_code,
      name,
      district,
    }));

  const rawQuery = normalize(question);
  const query = canonicalize(question);

  // ----------------------------------------------------------
  // 1. Explicit asset code in the user's question wins.
  // ----------------------------------------------------------
  const codeMatches = assets.filter((asset) => {
    const code = normalize(asset.asset_code);
    return code.length > 0 && rawQuery.includes(code);
  });

  if (codeMatches.length > 1) {
    throw new AmbiguousAssetError(choices(codeMatches));
  }

  if (codeMatches.length === 1) {
    return codeMatches[0];
  }

  // ----------------------------------------------------------
  // 2. Exact/canonical asset-name matches.
  //
  // IMPORTANT:
  // If TWO canonical records have the same matching name,
  // NEVER use selectedCode to silently choose one.
  // The user must disambiguate.
  // ----------------------------------------------------------
  const nameMatches = assets.filter((asset) => {
    const name = canonicalize(asset.name);

    if (!name || name.length < 3) return false;

    return query === name ||
      query.includes(name) ||
      rawQuery === normalize(asset.name) ||
      rawQuery.includes(normalize(asset.name));
  });

  if (nameMatches.length > 1) {
    throw new AmbiguousAssetError(choices(nameMatches));
  }

  if (nameMatches.length === 1) {
    return nameMatches[0];
  }

  // ----------------------------------------------------------
  // 3. Conservative fuzzy token matching.
  // Only resolve automatically when there is one clear winner.
  // ----------------------------------------------------------
  const queryTokens = new Set(
    query
      .split(" ")
      .filter(token =>
        token.length >= 3 &&
        ![
          "tell","about","show","give","what","which","where",
          "asset","information","info","explain","details",
          "inspection","inspections","maintenance","health",
          "risk","rul","record","records"
        ].includes(token)
      )
  );

  const scored = assets
    .map((asset) => {
      const name = canonicalize(asset.name);
      const nameTokens = new Set(
        name.split(" ").filter(token => token.length >= 2)
      );

      const overlap = [...nameTokens]
        .filter(token => queryTokens.has(token))
        .length;

      const denominator = Math.max(
        1,
        Math.min(nameTokens.size, queryTokens.size)
      );

      const tokenScore = overlap / denominator;

      const substringScore =
        query.includes(name) || name.includes(query)
          ? 1
          : 0;

      return {
        asset,
        score: Math.max(tokenScore, substringScore),
      };
    })
    .filter(row => row.score > 0)
    .sort((a,b) => b.score - a.score);

  if (scored.length > 0) {
    const bestScore = scored[0].score;

    const leaders = scored.filter(
      row => Math.abs(row.score - bestScore) < 0.0001
    );

    // A duplicated or equally strong match must remain ambiguous.
    if (bestScore >= 0.75 && leaders.length > 1) {
      throw new AmbiguousAssetError(
        choices(leaders.map(row => row.asset))
      );
    }

    const secondScore =
      scored.length > 1 ? scored[1].score : 0;

    // Resolve only a clear high-confidence winner.
    if (
      bestScore >= 0.75 &&
      bestScore - secondScore >= 0.20
    ) {
      return scored[0].asset;
    }
  }

  // ----------------------------------------------------------
  // 4. No asset was explicitly mentioned.
  // Continue using the UI-selected asset.
  // ----------------------------------------------------------
  const selected = assets.find(
    asset =>
      normalize(asset.asset_code) === normalize(selectedCode) ||
      normalize(asset.name) === normalize(selectedCode)
  );

  if (!selected) {
    throw new Error(`Asset with code ${selectedCode} not found.`);
  }

  return selected;
}

export function buildApplicationAiContext(assetCode: string, question: string) {
  const selected = db.getAsset(assetCode) ?? db.getAssets({limit:1000}).items.find(item => item.name.toLowerCase() === assetCode.toLowerCase());
  if (!selected) throw new Error(`Asset with code ${assetCode} not found.`);
  const assets = db.getAssets({ limit: 1000, sort_by: "name" }).items;
  const focus = resolveAsset(assets, assetCode, question);
  const inspections = db.getInspections(focus.asset_code);
  const maintenance = db.getMaintenance(focus.asset_code);
  const missing: string[] = [];
  if (!Object.keys(focus.dimensions ?? {}).length) missing.push("engineering_dimensions");
  if (inspections.length === 0) missing.push("inspection_history_and_defects");
  if (maintenance.length === 0) missing.push("maintenance_history");
  if (!focus.source_url) missing.push("government_source_link");
  if (!focus.assessment_basis) missing.push("assessment_basis");
  missing.push("independently_verified_assessment_calculation_and_timestamp");
  missing.push("verified_live_sensor_hydrology_weather_observations");
  missing.push("source_backed_report_documents");
  missing.push("official_government_evidence_documents");
  const highRisk = assets.filter((item) => item.risk_level === "HIGH");
  const query = question.toLowerCase();
  const related = assets.filter((item) =>
    item.asset_code.toLowerCase() !== focus.asset_code.toLowerCase() &&
    (query.includes(item.name.toLowerCase()) || query.includes(item.asset_code.toLowerCase()) ||
      (item.district.length > 3 && query.includes(item.district.toLowerCase()))),
  );
  return {
    question,
    selected_asset_code: selected.asset_code,
    focus_asset: focus,
    focus_asset_gis: { latitude: focus.latitude, longitude: focus.longitude, geometry: focus.geometry },
    focus_asset_digital_twin: { visual_strategy: focus.visual_strategy, fidelity_status: focus.fidelity_status, dimension_status: focus.dimension_status, dimensions: focus.dimensions },
    inspections: inspections.map(({ inspector_email, ...record }) => record),
    maintenance,
    registry_summary: {
      count: assets.length,
      high_risk_count: highRisk.length,
      high_risk_assets: highRisk.map(({ asset_code, name, district, risk_score, risk_level }) => ({ asset_code, name, district, risk_score, risk_level })),
      highest_stored_risk_score: assets.length ? Math.max(...assets.map((item) => item.risk_score ?? 0)) : null,
      matching_assets: related.slice(0, 30).map(({ asset_code, name, district, asset_type, risk_score, risk_level }) => ({ asset_code, name, district, asset_type, risk_score, risk_level })),
      matching_assets_truncated: related.length > 30,
    },
    government_evidence_documents: [],
    assessments: Object.fromEntries(['health','risk','rul'].map(key => [key, {value:null,status:'WITHHELD',method:'WITHHELD',reason:'No current validated assessment timestamp or calculation in this registry',stored_unverified_value: key === 'health' ? focus.health_score : key === 'risk' ? focus.risk_score : focus.rul_years}])),
    environment: [],
    source_references: focus.source_url ? [focus.source_url] : [],
    withheld_fields: ['health','risk','rul'].map(field => ({field,reason:'Current assessment evidence unavailable; stored estimates are unverified'})),
    terminology: { RUL: "Remaining Useful Life: an estimate of time before a defined serviceability or end-of-life criterion. A stored RUL number is not a live measurement or guaranteed remaining life." },
    workflow: {
      modules: ["Asset Registry", "GIS", "Digital Twin", "Inspections", "Maintenance", "Reports", "AI Engineering Advisor"],
      registration: "Authorized officers submit an asset, which is validated and added to the registry; GIS and asset search read that registry.",
      reports: "The application has a report view and export; no source-backed report document was retrieved for this request.",
    },
    provenance: "The local Express server loads a seeded JSON asset registry and seeded inspection/maintenance records; it is not the PostgreSQL database. Stored assessment scores and RUL are unverified application estimates without a current observation timestamp or independently audited calculation. No official government evidence documents were retrieved. Source URLs, reviewer comments, authority labels and an identity_status flag are not official evidence documents or proof of government approval. Generated dashboard telemetry and synthetic report summaries are excluded.",
    missing_evidence: missing,
  };
}

// -----------------------------------------------------------------------------
// Application-wide SIMRAS AI context.
//
// This context intentionally uses only records already present in SIMRAS.
// Missing evidence is reported instead of being fabricated.
// -----------------------------------------------------------------------------
export function buildApplicationGlobalAiContext(question: string) {
  const assets = db.getAssets({ limit: 5000, sort_by: "name" }).items;
  const inspections = db.getInspections();
  const maintenance = db.getMaintenance();

  const query = String(question ?? "").trim().toLowerCase();

  // If the user names one registered asset, automatically switch from
  // application-wide mode to the existing deep asset evidence context.
  const explicitMatches = assets.filter((asset) => {
    const code = asset.asset_code.toLowerCase();
    const name = asset.name.toLowerCase();

    return query.includes(code) ||
      (name.length >= 4 && query.includes(name));
  });

  if (explicitMatches.length > 1) {
    throw new AmbiguousAssetError(
      explicitMatches.slice(0, 20).map(({ asset_code, name, district }) => ({
        asset_code,
        name,
        district,
      })),
    );
  }

  if (explicitMatches.length === 1) {
    return {
      ...buildApplicationAiContext(explicitMatches[0].asset_code, question),
      scope: "ASSET_RESOLVED_FROM_GLOBAL",
    };
  }

  const byType = assets.reduce((acc: Record<string, number>, asset) => {
    const key = String(asset.asset_type || "unknown").toUpperCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const byDistrict = assets.reduce((acc: Record<string, number>, asset) => {
    const key = asset.district || "Unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const inspectionByAsset = inspections.reduce((acc: Record<string, number>, row: any) => {
    const key = String(row.asset_code || "UNKNOWN");
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const maintenanceByAsset = maintenance.reduce((acc: Record<string, number>, row: any) => {
    const key = String(row.asset_code || "UNKNOWN");
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const safeInspections = inspections.map((row: any) => {
    const { inspector_email, ...safe } = row;
    return safe;
  });

  const compactAssets = assets.map((asset) => ({
    asset_code: asset.asset_code,
    name: asset.name,
    asset_type: asset.asset_type,
    subtype: asset.subtype,
    district: asset.district,
    identity_status: asset.identity_status,
    condition: asset.condition,
    built_year: asset.built_year,
    material: asset.material,
    health_score: asset.health_score,
    risk_score: asset.risk_score,
    risk_level: asset.risk_level,
    rul_years: asset.rul_years,
    assessment_status: asset.assessment_status,
    assessment_basis: asset.assessment_basis,
    source_url: asset.source_url,
  }));

  const highRiskAssets = compactAssets.filter(
    (asset) => String(asset.risk_level).toUpperCase() === "HIGH",
  );

  const sourceReferences = Array.from(
    new Set(
      assets
        .map((asset) => asset.source_url)
        .filter((url): url is string => typeof url === "string" && url.length > 0),
    ),
  ).slice(0, 300);

  return {
    scope: "APPLICATION_GLOBAL",

    application: {
      name: "SIMRAS",
      full_name: "Smart Infrastructure Monitoring and Risk Assessment System",
      role: "Research and engineering decision-support application",
      total_assets: assets.length,
      total_inspections: inspections.length,
      total_maintenance: maintenance.length,
      high_risk_assets: highRiskAssets.length,
      infrastructure_by_type: byType,
      infrastructure_by_district: byDistrict,
    },

    workflow: {
      modules: [
        "Dashboard",
        "Asset Registry",
        "GIS",
        "Digital Twin",
        "Predictions",
        "Inspections",
        "Maintenance",
        "Reports",
        "Notifications",
        "AI Engineering Advisor",
      ],

      capabilities: {
        assets:
          "Stores and retrieves infrastructure identity, engineering and assessment information.",
        gis:
          "Displays registered infrastructure using stored coordinates and GIS geometry.",
        digital_twin:
          "Displays available asset geometry and source-backed engineering dimensions.",
        inspections:
          "Stores inspection date, type, condition rating, findings, defects and recommended actions where recorded.",
        maintenance:
          "Stores maintenance planning and status information where recorded.",
        predictions:
          "Displays stored Health, Risk and RUL values together with their available assessment status.",
        reports:
          "Provides selected-asset decision-support report data and export functionality.",
        advisor:
          "Answers questions from retrieved SIMRAS application evidence and identifies unavailable evidence.",
      },
    },

    registry_summary: {
      count: assets.length,
      by_type: byType,
      by_district: byDistrict,
      high_risk_count: highRiskAssets.length,
      high_risk_assets: highRiskAssets,
    },

    inspection_summary: {
      total: inspections.length,
      by_asset: inspectionByAsset,
    },

    maintenance_summary: {
      total: maintenance.length,
      by_asset: maintenanceByAsset,
    },

    // Compact records allow questions across the complete application registry.
    assets: compactAssets,

    // Do not transmit officer email addresses to Gemini.
    inspections: safeInspections.slice(0, 500),
    inspections_truncated: safeInspections.length > 500,

    maintenance: maintenance.slice(0, 500),
    maintenance_truncated: maintenance.length > 500,

    source_references: sourceReferences,

    provenance:
      "Application-wide context is retrieved from the current SIMRAS registry, inspection and maintenance stores. Asset-specific questions should use the deeper selected-asset evidence context. Stored values are not automatically official measurements.",

    terminology: {
      health:
        "Health score is an application assessment value and must be interpreted using its assessment status and provenance.",
      risk:
        "Risk score is an application assessment value and is not automatically an official structural inspection result.",
      RUL:
        "Remaining Useful Life is an estimate tied to a defined method and evidence basis; it is not a guaranteed service-life measurement.",
    },

    missing_evidence: [
      "Any fact not present in the retrieved SIMRAS records remains unavailable.",
      "A stored source URL alone does not prove an official inspection or approval.",
      "Do not infer missing inspection, defect, maintenance, traffic, hydrology, dimensions or government evidence.",
    ],
  };
}
