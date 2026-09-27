import { db, type AssetRecord } from './db';
import { buildAiContext } from './aiContext';

export function advisorAssetSummary(asset: AssetRecord) {
  return {
    asset_code: asset.asset_code, name: asset.name, asset_type: asset.asset_type,
    district: asset.district, identity_status: asset.identity_status,
    health_score: asset.health_score, risk_score: asset.risk_score, risk_level: asset.risk_level,
    rul_years: asset.rul_years, assessment_status: asset.assessment_status ?? 'REGISTRY_ASSESSMENT',
  };
}

// Explicit application knowledge only; do not read secrets, user profiles or arbitrary files.
const systemGuide = {
  name: 'SIMRAS — Smart Infrastructure Monitoring and Risk Assessment System',
  purpose: 'Infrastructure registry, GIS, digital twins, engineering evidence, assessments, inspections and maintenance for Andhra Pradesh.',
  categories: ['bridge', 'dam', 'barrage', 'airport', 'temple'],
  architecture: 'The main app uses React and TypeScript with Vite, an Express/Node server, a canonical asset registry and SQLite for persistent officer accounts and infrastructure registrations. Authentication uses bcrypt password hashes and JWT sessions. Gemini runs only through the server; credentials are never supplied to the advisor or frontend.',
  workflows: {
    account: 'Officer Login > Create Account. Enter officer name, email or username, password and confirmation. Accounts persist with hashed passwords. Existing sandbox role presets remain. No password-reset delivery or government-identity approval workflow is implemented.',
    registration: 'Officer Desk > Add Infrastructure. Complete Basic Info, Location, optional Engineering, Review, then Add Infrastructure. Name, type and valid coordinates are required. New records persist, appear in Assets/GIS, and remain pending verification/ML assessment with no invented Health, Risk or RUL.',
    navigation: 'Public portal: Home, GIS, Digital Twin, Reports and Report Hazard. Officer Desk: Dashboard, GIS Command, Digital Twin, Inspections, Maintenance, Reports, Review Queue, Notifications, Assets, Profile and Settings.',
    gis: 'Browse infrastructure on the map, filter the registry, select an asset and open its details.',
    twins: 'Digital twins visualize an asset and its available engineering dimensions. Procedural/simulated visualizations do not establish measured structural condition.',
    inspections: 'Officers record inspection findings; reviewer/admin roles can review submitted inspections. Seeded demonstration inspections are excluded from advisor evidence.',
    maintenance: 'The maintenance planner records planned work, priorities, schedules and status. A plan, tender or historical repair does not prove current condition or completed work.',
    reports: 'Asset reports expose available assessment, engineering and provenance information. The Reports page supports exports. Some legacy displays include illustrative/simulated telemetry; use retrieved source evidence for factual claims.',
    advisor: 'Ask about SIMRAS, any named asset, asset IDs, comparisons, inventory, engineering concepts or follow-up questions. Page selection is only an optional hint. The advisor provides information; it does not create records, change scores or approve work.',
  },
  metrics: {
    health: 'Health score is an assessment indicator. Its interpretation depends on the recorded assessment basis; it is not automatically a physical measurement.',
    risk: 'Risk score and risk level are decision-support assessments. Do not equate a score to a calibrated failure probability without supporting evidence.',
    rul: 'Remaining Useful Life (RUL) is a model/engineering estimate, not a guaranteed service life.',
    confidence: 'Prediction confidence and evidence completeness must be reported from available records, not invented.',
  },
  evidence_rules: 'Separate official source evidence, model predictions, sparse estimates, unverified officer submissions, historical evidence and unavailable evidence. Live/simulated telemetry is not supplied as measurement. General engineering explanations must be labeled as general guidance, not an asset-specific finding or certification.',
};

export function buildAdvisorDirectory(selectedAssetCode?: string) {
  const result = db.getAssets({ limit: 1000, sort_by: 'name' });
  // Count across pages so aggregate answers stay accurate as the registry grows.
  const all = [...result.items];
  for (let offset = 1000; offset < result.total; offset += 1000) all.push(...db.getAssets({ limit: 1000, offset, sort_by: 'name' }).items);
  const selected = selectedAssetCode ? db.getAsset(selectedAssetCode) : undefined;
  return {
    system: systemGuide,
    summary: {
      total: result.total,
      by_type: all.reduce((counts, asset) => { counts[asset.asset_type] = (counts[asset.asset_type] ?? 0) + 1; return counts; }, {} as Record<string, number>),
      by_risk_level: all.reduce((counts, asset) => { const level = asset.risk_level ?? 'UNAVAILABLE'; counts[level] = (counts[level] ?? 0) + 1; return counts; }, {} as Record<string, number>),
      pending_assessment: all.filter(asset => asset.assessment_status === 'MODEL_PENDING').length,
    },
    selected_asset_hint: selected ? advisorAssetSummary(selected) : null,
    directory_truncated: result.total > result.items.length,
    // Keep the discovery directory small. Read full metrics/evidence only for relevant assets.
    assets: result.items.map(({ asset_code, name, asset_type, district }) => ({ asset_code, name, asset_type, district })),
  };
}

export function readAdvisorAssets(codes: unknown, question: string) {
  const result: { assets: ReturnType<typeof buildAiContext>[]; not_found: string[]; error?: string } = { assets: [], not_found: [] };
  if (!Array.isArray(codes) || !codes.length || codes.length > 8 || codes.some(code => typeof code !== 'string' || code.length > 128)) {
    return { ...result, error: 'Supply between 1 and 8 exact asset identifiers from the registry.' };
  }
  for (const code of new Set<string>(codes)) {
    if (db.getAsset(code)) result.assets.push(buildAiContext(code, question));
    else result.not_found.push(code);
  }
  return result;
}

export function searchAdvisorAssets(args: Record<string, unknown>) {
  const query = typeof args.query === 'string' ? args.query.slice(0, 200) : undefined;
  const type = typeof args.asset_type === 'string' ? args.asset_type : undefined;
  const district = typeof args.district === 'string' ? args.district : undefined;
  const offset = typeof args.offset === 'number' && Number.isInteger(args.offset) && args.offset >= 0 ? args.offset : 0;
  const sort = args.sort_by === 'risk_score' || args.sort_by === 'health_score' ? args.sort_by : 'name';
  const result = db.getAssets({ search: query, asset_type: type, district, offset, limit: 30, sort_by: sort });
  return { ...result, items: result.items.map(advisorAssetSummary) };
}
