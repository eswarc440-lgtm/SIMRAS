import { describe, expect, it } from "vitest";
import { buildApplicationAiContext, trimConversationHistory } from "./aiContext";

describe("AI context retrieval", () => {
  it("loads selected asset evidence without synthetic live data", () => {
    const context = buildApplicationAiContext("AP_DAM_00001", "What was its latest inspection?");
    expect(context.focus_asset.asset_code).toBe("AP_DAM_00001");
    expect(context.inspections.length).toBeGreaterThan(0);
    expect(context).not.toHaveProperty("telemetry");
    expect(context.missing_evidence).toContain("verified_live_sensor_hydrology_weather_observations");
    expect(context.government_evidence_documents).toEqual([]);
    expect(context.registry_summary.high_risk_count).toBe(0);
  });

  it("keeps recent valid session messages", () => {
    const history = Array.from({ length: 20 }, (_, index) => ({ role: index % 2 ? "assistant" : "user", content: `message ${index}` })) as any;
    const trimmed = trimConversationHistory(history);
    expect(trimmed).toHaveLength(8);
    expect(trimmed[0].content).toBe("message 12");
  });
});
