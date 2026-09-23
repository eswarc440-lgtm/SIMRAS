import { describe, expect, it } from "vitest";
import { buildAiContext, trimConversationHistory } from "./aiContext";

describe("AI context retrieval", () => {
  it("loads selected asset evidence for follow-up questions", () => {
    const context = buildAiContext("AP_DAM_00001", "What was its latest inspection?");
    expect(context.asset?.asset_code).toBe("AP_DAM_00001");
    expect(context.missing_evidence).not.toContain("asset_registry");
    expect(context.inspections.length).toBeGreaterThan(0);
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
});
