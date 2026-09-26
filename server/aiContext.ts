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

export function resolveAsset<T extends {asset_code:string;name:string;district?:string}>(assets:T[], selectedCode:string, question:string):T {
  const query = question.trim().toLowerCase();
  const codeMatches = assets.filter(a => query.includes(a.asset_code.toLowerCase()));
  const nameMatches = assets.filter(a => query.includes(a.name.toLowerCase()));
  const matches = codeMatches.length ? codeMatches : nameMatches;
  if (matches.length > 1) throw new AmbiguousAssetError(matches.map(({asset_code,name,district})=>({asset_code,name,district})));
  const selected = matches[0] ?? assets.find(a => a.asset_code.toLowerCase() === selectedCode.toLowerCase() || a.name.toLowerCase() === selectedCode.toLowerCase());
  if (!selected) throw new Error(`Asset with code ${selectedCode} not found.`);
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
