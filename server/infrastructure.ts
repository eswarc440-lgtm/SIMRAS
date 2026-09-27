import { randomUUID } from 'node:crypto';
import type { AssetRecord } from './db';

export class RequestError extends Error {
  constructor(message: string, public status = 400) { super(message); }
}
function optionalText(value: unknown, label: string, max = 200): string {
  if (value === undefined || value === null) return '';
  if (typeof value !== 'string' || value.length > max) throw new RequestError(`Invalid ${label}`);
  return value.trim();
}
function numeric(value: unknown, label: string, min: number, max: number): number {
  if ((typeof value !== 'number' && typeof value !== 'string') || String(value).trim() === '') throw new RequestError(`${label} is required`);
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || number > max) throw new RequestError(`Invalid ${label}`);
  return number;
}
export function parseInfrastructure(body: any): AssetRecord {
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new RequestError('Invalid infrastructure request');
  const name = optionalText(body.name, 'infrastructure name');
  const type = body.asset_type ?? body.type;
  if (!name) throw new RequestError('Infrastructure name is required');
  if (!['bridge', 'dam', 'barrage', 'airport', 'temple'].includes(type)) throw new RequestError('Invalid infrastructure type');
  const latitude = numeric(body.latitude, 'latitude', -90, 90);
  const longitude = numeric(body.longitude, 'longitude', -180, 180);
  const code = optionalText(body.asset_code, 'asset identifier', 100) || `AP_${type.toUpperCase()}_${randomUUID()}`;
  if (!/^[a-zA-Z0-9_-]+$/.test(code)) throw new RequestError('Invalid asset identifier');
  const dimensions: Record<string, number> = {};
  if (body.dimensions !== undefined) {
    if (!body.dimensions || typeof body.dimensions !== 'object' || Array.isArray(body.dimensions)) throw new RequestError('Invalid engineering dimensions');
    const fields = ['length_m', 'height_m', 'width_m', 'deck_width_m', 'span_count', 'pier_count', 'element_count'];
    for (const [key, value] of Object.entries(body.dimensions)) {
      if (!fields.includes(key)) throw new RequestError(`Unsupported engineering dimension: ${key}`);
      dimensions[key] = numeric(value, key, 0, 10000000);
    }
  }
  const builtYear = body.built_year == null || body.built_year === '' ? null : numeric(body.built_year, 'built year', 1, new Date().getFullYear());
  if (builtYear !== null && !Number.isInteger(builtYear)) throw new RequestError('Invalid built year');
  const sourceUrl = optionalText(body.source_url, 'source URL', 2048);
  if (sourceUrl && !/^https?:\/\//i.test(sourceUrl)) throw new RequestError('Source URL must use HTTP or HTTPS');
  return {
    asset_code: code, name, asset_type: type, subtype: optionalText(body.subtype, 'subtype'),
    district: optionalText(body.district, 'district'), latitude, longitude,
    geometry: { type: 'Point', coordinates: [longitude, latitude] }, priority: 2,
    visual_strategy: 'PROCEDURAL_PENDING_EVIDENCE', dimension_authority: optionalText(body.dimension_authority, 'dimension authority'),
    fidelity_status: 'PENDING_EVIDENCE', dimension_status: 'OFFICER_SUBMITTED_UNVERIFIED', dimensions,
    built_year: builtYear, material: optionalText(body.material, 'material'), condition: 'UNASSESSED',
    health_score: null, risk_score: null, risk_level: null, rul_years: null, prediction_confidence: null,
    assessment_basis: 'OFFICER_SUBMITTED: Evidence verification and ML assessment pending', assessment_status: 'MODEL_PENDING',
    source_url: sourceUrl || undefined, identity_status: 'PENDING_VERIFICATION', created_at: new Date().toISOString(),
  };
}
