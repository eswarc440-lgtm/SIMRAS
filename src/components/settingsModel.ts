export const defaultPreferences = {
  general: { landingPage: "dashboard", assetCategory: "ALL", dateFormat: "DD/MM/YYYY", timeFormat: "24h", units: "metric" },
  notifications: { inspectionDue: true, inspectionOverdue: true, maintenanceDue: true, maintenanceOverdue: true, riskAlerts: true, highRiskAssets: true, reviewAssignments: true, approvalResults: true, evidenceConflicts: true },
  gis: { defaultLayer: "street", markerClustering: true, rememberLastPosition: true, defaultRiskFilter: "ALL", showUnmappedAssets: true },
  twin: { defaultCamera: "perspective", showDimensions: true, autoFit: true, showDefects: true, showLabels: true, renderingQuality: "auto" },
  reports: { includeGraphs: true, includeTwinSnapshot: true, exportType: "PDF" },
  ai: { useSelectedAsset: true, showSources: true, showLimitations: true, responseDetail: "standard" },
  accessibility: { textSize: "default", reducedMotion: false, highContrast: false },
};
export type Preferences = typeof defaultPreferences;
export function mergePreferences(base: Preferences, patch: Record<string, any>): Preferences {
  return Object.fromEntries(Object.entries(base).map(([section, values]) => [section, { ...values, ...(patch[section] ?? {}) }])) as Preferences;
}
