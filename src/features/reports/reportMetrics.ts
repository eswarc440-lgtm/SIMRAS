export function reportMetrics(assessment:any, prediction?:any) {
  if (assessment.status === 'WITHHELD') return {health:null,risk:null,rul:null,riskTier:'WITHHELD'};
  return {health:prediction?.predicted_health_score ?? assessment.health_score ?? null,
    risk:prediction?.predicted_failure_risk_pct ?? assessment.risk_score ?? null,
    rul:prediction?.predicted_rul_years ?? assessment.rul_years ?? null,
    riskTier:prediction?.risk_tier ?? assessment.risk_level ?? 'WITHHELD'};
}
