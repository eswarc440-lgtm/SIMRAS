import { describe, it, expect } from "vitest";
import { buildApplicationGlobalAiContext } from "./aiContext";
import { askGlobalAssistant } from "./ai";

describe("SIMRAS global engineering advisor", () => {
  it("builds application-wide evidence without requiring a selected asset", () => {
    const context: any = buildApplicationGlobalAiContext("How many assets and inspections are in SIMRAS?");
    expect(context.scope).toBe("APPLICATION_GLOBAL");
    expect(context.application.total_assets).toBeGreaterThan(0);
    expect(typeof context.application.total_inspections).toBe("number");
    expect(typeof context.application.total_maintenance).toBe("number");
    expect(Array.isArray(context.assets)).toBe(true);
  });

  it("sends global application evidence to the AI provider", async () => {
    const result = await askGlobalAssistant(
      "Explain the SIMRAS inspection system",
      [],
      async (question, context) => {
        expect(question).toContain("inspection");
        expect(context.scope).toBe("APPLICATION_GLOBAL");
        return "Global SIMRAS answer";
      },
      async () => ({
        scope: "APPLICATION_GLOBAL",
        application: {
          total_assets: 10,
          total_inspections: 3,
          total_maintenance: 2
        },
        assets: [],
        inspections: [],
        maintenance: [],
        source_references: [],
        missing_evidence: []
      })
    );

    expect(result.answer).toBe("Global SIMRAS answer");
    expect(result.ai_generated).toBe(true);
  });
});