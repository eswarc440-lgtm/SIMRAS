import { db } from "./db";

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export function trimConversationHistory(history: ConversationMessage[] = []) {
  return history
    .filter((message) => (message.role === "user" || message.role === "assistant") && typeof message.content === "string" && message.content.trim())
    .slice(-10);
}

export function buildAiContext(assetCode: string, question: string) {
  const asset = db.getAsset(assetCode);
  if (!asset) throw new Error(`Asset with code ${assetCode} not found.`);
  const inspections = db.getInspections(assetCode).slice(0, 5);
  const maintenance = db.getMaintenance(assetCode).slice(0, 5);
  const telemetry = db.getTelemetry(assetCode) ?? null;
  const missing: string[] = [];
  if (!asset) missing.push("asset_registry");
  if (inspections.length === 0) missing.push("inspection_history");
  if (maintenance.length === 0) missing.push("maintenance_history");
  if (!telemetry) missing.push("telemetry");

  return {
    question,
    asset,
    assessment: {
      health_score: asset.health_score ?? null,
      risk_score: asset.risk_score ?? null,
      risk_level: asset.risk_level ?? null,
      rul_years: asset.rul_years ?? null,
      assessment_basis: asset.assessment_basis ?? null,
    },
    engineering_dimensions: asset.dimensions ?? {},
    inspections,
    maintenance,
    telemetry,
    source: {
      authority: asset.dimension_authority ?? null,
      url: asset.source_url ?? null,
      identity_status: asset.identity_status,
    },
    missing_evidence: missing,
  };
}
