import type { AIInsight, ModelMetrics, NotificationItem, Prediction, ReportItem, TrendPoint } from "../types";

export const healthTrend: TrendPoint[] = [
  { period: "Feb", healthy: 880, warning: 312, critical: 92, predictions: 12, riskIndex: 44 },
  { period: "Mar", healthy: 894, warning: 305, critical: 88, predictions: 15, riskIndex: 42 },
  { period: "Apr", healthy: 903, warning: 298, critical: 85, predictions: 17, riskIndex: 41 },
  { period: "May", healthy: 912, warning: 291, critical: 82, predictions: 19, riskIndex: 38 },
  { period: "Jun", healthy: 921, warning: 286, critical: 79, predictions: 21, riskIndex: 36 },
  { period: "Jul", healthy: 928, warning: 281, critical: 76, predictions: 23, riskIndex: 34 },
  { period: "Aug", healthy: 934, warning: 276, critical: 74, predictions: 25, riskIndex: 32 },
];

export const riskDistribution = [
  { name: "Low Risk", value: 934, key: "low" },
  { name: "Medium Risk", value: 276, key: "medium" },
  { name: "High Risk", value: 74, key: "high" },
];

export const regionalAnalysis = [
  { region: "NTR", assets: 268, atRisk: 74, riskIndex: 31 },
  { region: "Guntur", assets: 224, atRisk: 63, riskIndex: 36 },
  { region: "Visakhapatnam", assets: 246, atRisk: 82, riskIndex: 42 },
  { region: "East Godavari", assets: 188, atRisk: 51, riskIndex: 34 },
  { region: "Tirupati", assets: 172, atRisk: 44, riskIndex: 28 },
  { region: "Anantapur", assets: 186, atRisk: 36, riskIndex: 24 },
];

export const predictions: Prediction[] = [
  {
    id: "PR-9001",
    assetId: "BR-104",
    assetName: "Rajiv Bridge",
    prediction: "Structural condition decline within 6 months",
    risk: "high",
    confidence: 94.2,
    predictedAt: "09 Aug 2026",
  },
  {
    id: "PR-9002",
    assetId: "BL-302",
    assetName: "Municipal Administration Building",
    prediction: "Load capacity reduction, restricted usage advised",
    risk: "high",
    confidence: 91.6,
    predictedAt: "09 Aug 2026",
  },
  {
    id: "PR-9003",
    assetId: "BR-390",
    assetName: "Godavari Rail Bridge Approach",
    prediction: "Foundation scour progression during monsoon",
    risk: "high",
    confidence: 89.4,
    predictedAt: "08 Aug 2026",
  },
  {
    id: "PR-9004",
    assetId: "RD-204",
    assetName: "Central Ring Road",
    prediction: "Pavement fatigue cracking within 12 months",
    risk: "medium",
    confidence: 86.1,
    predictedAt: "08 Aug 2026",
  },
  {
    id: "PR-9005",
    assetId: "UT-407",
    assetName: "Northern Distribution Substation",
    prediction: "Equipment degradation, maintenance window recommended",
    risk: "medium",
    confidence: 83.7,
    predictedAt: "07 Aug 2026",
  },
  {
    id: "PR-9006",
    assetId: "OT-602",
    assetName: "Coastal Retaining Wall Section 12",
    prediction: "Erosion-driven stability loss under storm loading",
    risk: "medium",
    confidence: 81.2,
    predictedAt: "07 Aug 2026",
  },
  {
    id: "PR-9007",
    assetId: "BR-221",
    assetName: "Kanaka Durga Flyover",
    prediction: "Condition stable through next inspection cycle",
    risk: "low",
    confidence: 96.3,
    predictedAt: "06 Aug 2026",
  },
  {
    id: "PR-9008",
    assetId: "WT-118",
    assetName: "Prakasam Barrage Regulator",
    prediction: "Gate mechanism performance within nominal range",
    risk: "low",
    confidence: 92.8,
    predictedAt: "06 Aug 2026",
  },
];

export const insights: AIInsight[] = [
  {
    id: "IN-01",
    title: "Rising structural risk on Bridge BR-104",
    body: "Bridge BR-104 shows increasing structural risk indicators across the last three inspection cycles.",
    assetId: "BR-104",
    risk: "high",
    confidence: 94.2,
  },
  {
    id: "IN-02",
    title: "Monsoon exposure cluster in East Godavari",
    body: "Four assets in the East Godavari corridor share scour-related risk drivers ahead of the monsoon window.",
    assetId: "BR-390",
    risk: "high",
    confidence: 88.5,
  },
  {
    id: "IN-03",
    title: "Pavement fatigue trend on ring corridor",
    body: "Central Ring Road segments show a consistent surface deterioration slope over six months.",
    assetId: "RD-204",
    risk: "medium",
    confidence: 86.1,
  },
  {
    id: "IN-04",
    title: "Stable portfolio in Anantapur",
    body: "Anantapur assets maintain the lowest regional risk index with no escalation predicted.",
    assetId: "UT-521",
    risk: "low",
    confidence: 95.0,
  },
];

export const models: ModelMetrics[] = [
  { name: "Health Score Model", version: "v3.2.1", r2: 0.966, mae: 2.41, rmse: 3.18, trainedAt: "28 Jul 2026" },
  { name: "Risk Classification Model", version: "v3.1.0", r2: 0.942, mae: 3.07, rmse: 4.12, trainedAt: "24 Jul 2026" },
  { name: "Remaining Useful Life Model", version: "v2.8.4", r2: 0.918, mae: 1.12, rmse: 1.74, trainedAt: "18 Jul 2026" },
];

export const modelEvaluation = [
  { epoch: "E1", actual: 62, predicted: 59 },
  { epoch: "E2", actual: 68, predicted: 66 },
  { epoch: "E3", actual: 71, predicted: 70 },
  { epoch: "E4", actual: 75, predicted: 76 },
  { epoch: "E5", actual: 79, predicted: 78 },
  { epoch: "E6", actual: 84, predicted: 83 },
  { epoch: "E7", actual: 88, predicted: 89 },
];

export const reports: ReportItem[] = [
  {
    id: "RP-1201",
    title: "Infrastructure Risk Assessment",
    category: "AI Prediction",
    type: "AI Analysis",
    generated: "09 Aug 2026",
    status: "Ready",
    summary: "Portfolio-wide risk scoring across 1,284 monitored assets with model confidence breakdown.",
    pages: 24,
  },
  {
    id: "RP-1198",
    title: "Bridge Condition Summary — Zone II",
    category: "Infrastructure",
    type: "Condition Report",
    generated: "08 Aug 2026",
    status: "Ready",
    summary: "Structural condition ratings for 214 bridge assets including inspection deltas.",
    pages: 18,
  },
  {
    id: "RP-1190",
    title: "High Risk Asset Register",
    category: "Risk",
    type: "Risk Register",
    generated: "06 Aug 2026",
    status: "Ready",
    summary: "Consolidated register of assets exceeding the high-risk threshold with recommended actions.",
    pages: 11,
  },
  {
    id: "RP-1184",
    title: "Regional Analytics Digest",
    category: "Analytics",
    type: "Analytics",
    generated: "04 Aug 2026",
    status: "Processing",
    summary: "District-level infrastructure health trends and risk index comparison.",
    pages: 32,
  },
  {
    id: "RP-1177",
    title: "Quarterly Inspection Compliance",
    category: "Inspection",
    type: "Inspection",
    generated: "01 Aug 2026",
    status: "Ready",
    summary: "Inspection completion rate, overdue assets and field observation summary.",
    pages: 15,
  },
  {
    id: "RP-1165",
    title: "Model Performance Evaluation",
    category: "AI Prediction",
    type: "AI Analysis",
    generated: "28 Jul 2026",
    status: "Archived",
    summary: "Evaluation of health, risk and remaining useful life models against validation data.",
    pages: 9,
  },
];

export const notifications: NotificationItem[] = [
  {
    id: "NT-01",
    title: "AI Risk Alert",
    body: "Bridge BR-104 risk level increased to High following the latest prediction cycle.",
    severity: "critical",
    time: "12 minutes ago",
    read: false,
  },
  {
    id: "NT-02",
    title: "Inspection Reminder",
    body: "Inspection due for Road RD-204 within the next 7 days.",
    severity: "warning",
    time: "2 hours ago",
    read: false,
  },
  {
    id: "NT-03",
    title: "System Update",
    body: "New analytics data available for the Visakhapatnam region.",
    severity: "info",
    time: "Yesterday",
    read: true,
  },
  {
    id: "NT-04",
    title: "Model Retrained",
    body: "Health Score Model v3.2.1 deployed with R² 0.966.",
    severity: "info",
    time: "2 days ago",
    read: true,
  },
  {
    id: "NT-05",
    title: "Critical Condition Flag",
    body: "Municipal Administration Building BL-302 moved to Restricted status.",
    severity: "critical",
    time: "3 days ago",
    read: true,
  },
];

export const recentActivity = [
  { id: "AC-1", actor: "AI Engine", action: "Generated 25 risk predictions", time: "09 Aug 2026 · 06:10" },
  { id: "AC-2", actor: "Zone II Inspection Cell", action: "Uploaded inspection for BR-104", time: "08 Aug 2026 · 17:42" },
  { id: "AC-3", actor: "Analytics Service", action: "Refreshed regional risk index", time: "08 Aug 2026 · 09:05" },
  { id: "AC-4", actor: "R. Prasad", action: "Downloaded High Risk Asset Register", time: "07 Aug 2026 · 15:20" },
  { id: "AC-5", actor: "GIS Service", action: "Synced 1,284 asset geometries", time: "07 Aug 2026 · 08:00" },
];
