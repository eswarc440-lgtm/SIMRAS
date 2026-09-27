import fs from 'node:fs';
import path from 'node:path';
import type { AssetRecord } from './db';

// Read-only CSV reader, including quoted commas/newlines. Cache by modification time.
const cache = new Map<string, { modified: number; rows: Record<string, string>[] }>();
export function readEvidenceCsv(relativePath: string): Record<string, string>[] {
  const file = path.resolve(relativePath);
  if (!fs.existsSync(file)) return [];
  const modified = fs.statSync(file).mtimeMs;
  if (cache.get(file)?.modified === modified) return cache.get(file)!.rows;
  const input = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
  const records: string[][] = [];
  let row: string[] = [], field = '', quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '"') {
      if (quoted && input[i + 1] === '"') { field += '"'; i++; } else quoted = !quoted;
    } else if (char === ',' && !quoted) { row.push(field); field = ''; }
    else if (char === '\n' && !quoted) { row.push(field.replace(/\r$/, '')); records.push(row); row = []; field = ''; }
    else field += char;
  }
  if (row.length || field) { row.push(field.replace(/\r$/, '')); records.push(row); }
  const headers = records.shift() ?? [];
  const rows = records.filter(values => values.length === headers.length).map(values => Object.fromEntries(headers.map((key, i) => [key, values[i]])));
  cache.set(file, { modified, rows });
  return rows;
}

export function retrieveAssetEvidence(asset: AssetRecord) {
  const sourceFiles = {
    predictions: 'backend/data/processed/bridge/AP_ALL_BRIDGES_NUMERIC_PREDICTIONS.csv',
    environment: 'backend/data/processed/bridge/AP_ALL_BRIDGES_ENVIRONMENT_ENRICHED.csv',
    readiness: 'backend/data/processed/bridge/AP_BRIDGE_PRODUCTION_REGISTRY.csv',
    engineering: 'backend/data/processed/bridge/AP_BRIDGE_ENGINEERING_EVIDENCE.csv',
    verified: 'backend/data/bridge_inspections/AP_BRIDGE_VERIFIED_EVIDENCE_V1.csv',
    maintenance: 'backend/data/bridge_inspections/AP_BRIDGE_MAINTENANCE_EVIDENCE_V1.csv',
    hydrologyMatches: 'backend/data/processed/dam_barrage/AP_HYDROLOGY_ASSET_MATCHES.csv',
    hydrologyFeatures: 'backend/data/processed/dam_barrage/AP_DAM_BARRAGE_HYDROLOGY_FEATURES_V1.csv',
  };
  const matches = (row: Record<string, string>) => {
    const code = row.asset_code || row.canonical_asset_code;
    if (code === asset.asset_code) return true;
    // Exact name plus nearby coordinates permits the canonical bridge-code crosswalk.
    const name = row.bridge_name || row.asset_match_name || row.asset_name;
    if (name?.trim().toLowerCase() !== asset.name.trim().toLowerCase()) return false;
    if (row.latitude && row.longitude) return Math.abs(Number(row.latitude) - asset.latitude) < 0.02 && Math.abs(Number(row.longitude) - asset.longitude) < 0.02;
    return !code;
  };
  const artifacts: string[] = [];
  const select = (key: keyof typeof sourceFiles) => {
    const rows = readEvidenceCsv(sourceFiles[key]).filter(matches).slice(0, 30);
    if (rows.length) artifacts.push(sourceFiles[key]);
    return rows;
  };
  // New submissions cannot acquire evidence merely by choosing an existing asset name.
  if (asset.assessment_status === 'MODEL_PENDING') return { predictions: [], environment: [], readiness: [], engineering: [], verified: [], maintenance: [], hydrology: [], artifacts };
  const predictions = select('predictions'), environment = select('environment'), readiness = select('readiness');
  const engineering = select('engineering').filter(row => row.is_synthetic?.toLowerCase() !== 'true');
  const verified = select('verified'), maintenance = select('maintenance');
  const links = select('hydrologyMatches').filter(row => /^(MATCHED_HIGH|MATCHED|VERIFIED|AUTO_MATCHED|ACCEPTED)$/.test(row.match_status));
  const ids = new Set(links.map(row => Number(row.asset_id)));
  const hydrology = ids.size ? readEvidenceCsv(sourceFiles.hydrologyFeatures).filter(row => ids.has(Number(row.asset_id))).slice(0, 20) : [];
  if (hydrology.length) artifacts.push(sourceFiles.hydrologyFeatures);
  return { predictions, environment, readiness, engineering, verified, maintenance, hydrology, artifacts };
}
