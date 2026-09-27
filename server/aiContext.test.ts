import { describe, expect, it } from "vitest";
import { buildAiContext, trimConversationHistory } from "./aiContext";

describe("AI context retrieval", () => {
  it("loads selected asset evidence for follow-up questions", () => {
    const context = buildAiContext("AP_DAM_00001", "What was its latest inspection?");
    expect(context.asset?.asset_code).toBe("AP_DAM_00001");
    expect(context.missing_evidence).not.toContain("asset_registry");
    expect(context.inspections.every((record: any) => record.evidence_status !== 'SIMULATED')).toBe(true);
    expect(context.telemetry).toBeNull();
    expect(context.evidence_status.telemetry).toBe('UNAVAILABLE');
  });

  it("reports unavailable evidence instead of inventing it", () => {
    const context = buildAiContext("AP_DAM_00001", "Show evidence");
    if (context.telemetry === null) expect(context.missing_evidence).toContain("telemetry");
  });

  it("retains only recent valid session messages", () => {
    const history = Array.from({ length: 20 }, (_, index) => ({ role: index % 2 ? "assistant" : "user", content: `message ${index}` })) as any;
    const trimmed = trimConversationHistory(history);
    expect(trimmed).toHaveLength(10);
    expect(trimmed[0].content).toBe("message 10");
  });

  it('loads sparse bridge predictions and source provenance without promoting them to measurements', () => {
    const context = buildAiContext('AP_BR_00002', 'Explain its scores');
    expect(context.assessment.prediction_confidence).toBe(0.81);
    expect(context.evidence_status.assessment).toBe('SPARSE_MODEL_ESTIMATE');
    expect(context.source.artifacts.length).toBeGreaterThan(0);
    expect(context.telemetry).toBeNull();
  });

  it('rejects an unknown selected asset and safely trims malformed history', () => {
    expect(() => buildAiContext('missing-asset', 'Explain')).toThrow();
    expect(trimConversationHistory(null as any)).toEqual([]);
    expect(trimConversationHistory([null, {}, { role: 'user', content: 'valid' }] as any)).toEqual([{ role: 'user', content: 'valid' }]);
  });

  it('loads hydrology features only through a high-confidence matched asset link', () => {
    const context = buildAiContext('AP_DAM_WRIS_AP01HH0127', 'What hydrology evidence is available?');
    expect(context.environment.hydrology.length).toBeGreaterThan(0);
    expect(context.environment.hydrology.every(row => Number(row.asset_id) === 35)).toBe(true);
    expect(context.source.artifacts).toContain('backend/data/processed/dam_barrage/AP_DAM_BARRAGE_HYDROLOGY_FEATURES_V1.csv');
  });
});
