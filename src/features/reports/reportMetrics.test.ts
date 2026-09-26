import {describe,expect,it} from 'vitest';
import {reportMetrics} from './reportMetrics';

describe('report assessment display', () => {
  it('keeps withheld values null even when a previous asset had a prediction', () => {
    expect(reportMetrics({status:'WITHHELD'}, {predicted_health_score:78.5,predicted_failure_risk_pct:21.5,predicted_rul_years:39.7,risk_tier:'LOW'}))
      .toEqual({health:null,risk:null,rul:null,riskTier:'WITHHELD'});
  });
  it('does not invent defaults for missing evidence and preserves measured zero', () => {
    expect(reportMetrics({}).health).toBeNull();
    expect(reportMetrics({health_score:0,risk_score:0,rul_years:0,risk_level:'LOW'}))
      .toEqual({health:0,risk:0,rul:0,riskTier:'LOW'});
  });
});
