import { db } from "./db";
import { retrieveAssetEvidence } from './evidenceSources';

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export function trimConversationHistory(history: ConversationMessage[] = []) {
  return (Array.isArray(history) ? history : [])
    .filter((message) => message && (message.role === "user" || message.role === "assistant") && typeof message.content === "string" && message.content.trim())
    .slice(-10).map(message => ({ role: message.role, content: message.content.slice(0, 4000) }));
}

export function buildAiContext(assetCode: string, question: string) {
  const asset = db.getAsset(assetCode);
  if (!asset) throw new Error(`Asset with code ${assetCode} not found.`);
  const evidence = retrieveAssetEvidence(asset);
  const inspections = db.getRecordedInspections(assetCode).slice(0, 5).map(({ inspector_email, ...record }) => ({ ...record, evidence_status: 'OFFICER_RECORDED_NOT_INDEPENDENTLY_VERIFIED' }));
  const maintenance = db.getRecordedMaintenance(assetCode).slice(0, 5).map(record => ({ ...record, evidence_status: 'OFFICER_RECORDED_NOT_INDEPENDENTLY_VERIFIED' }));
  // db.getTelemetry is a simulator, not an ingestion source. Never send its readings as evidence.
  const telemetry = null;
  const prediction = evidence.predictions[0];
  const predictionConfidence = prediction?.prediction_confidence ? Number(prediction.prediction_confidence) : asset.prediction_confidence ?? null;
  const assessmentStatus = asset.health_score == null ? 'UNAVAILABLE' : prediction?.prediction_mode || (/ML_VALIDATED/.test(asset.assessment_basis) ? 'MODEL_PREDICTION' : 'SPARSE_MODEL_ESTIMATE');
  const missing: string[] = [];
  if (!asset) missing.push("asset_registry");
  if (inspections.length === 0) missing.push("inspection_history");
  if (maintenance.length === 0) missing.push("maintenance_history");
  if (!telemetry) missing.push("telemetry");
  if (!evidence.environment.length) missing.push('rainfall');
  if (!evidence.hydrology.length && !evidence.environment.some(row => row.river_discharge_mean_m3s)) missing.push('hydrology');
  if (!evidence.readiness.some(row => row.aadt)) missing.push('traffic');
  if (predictionConfidence == null) missing.push('prediction_confidence');

  return {
    question,
    asset,
    assessment: {
      health_score: asset.health_score ?? null,
      risk_score: asset.risk_score ?? null,
      risk_level: asset.risk_level ?? null,
      rul_years: asset.rul_years ?? null,
      assessment_basis: asset.assessment_basis ?? null,
      prediction_confidence: predictionConfidence,
      assessment_status: asset.assessment_status ?? assessmentStatus,
      linked_model_predictions: evidence.predictions,
      ml_readiness: evidence.readiness,
    },
    engineering_dimensions: asset.dimensions ?? {},
    inspections,
    maintenance,
    telemetry,
    environment: { rainfall_and_river_observations: evidence.environment, hydrology: evidence.hydrology, traffic: evidence.readiness.filter(row => row.aadt).map(row => ({ aadt: row.aadt, heavy_vehicle_pct: row.heavy_vehicle_pct, traffic_status: row.traffic_status })) },
    official_source_records: { engineering: evidence.engineering, verified_evidence: evidence.verified, historical_maintenance: evidence.maintenance },
    evidence_status: {
      assessment: assessmentStatus,
      dimensions: asset.dimension_status,
      telemetry: 'UNAVAILABLE',
      inspections: inspections.length ? 'OFFICER_RECORDED_NOT_INDEPENDENTLY_VERIFIED' : 'UNAVAILABLE',
      interpretation: 'Registry scores and linked CSV predictions can differ. Identify their provenance and never call either an official structural measurement. Historical maintenance is not a current inspection. Spatially matched rainfall and river observations are station proxies, not on-structure sensors. ML readiness may withhold official scores even when sparse estimates exist. Seeded demo inspections and simulated telemetry are excluded.',
    },
    source: {
      authority: asset.dimension_authority ?? null,
      url: asset.source_url ?? null,
      identity_status: asset.identity_status,
      artifacts: evidence.artifacts,
    },
    missing_evidence: missing,
  };
}
