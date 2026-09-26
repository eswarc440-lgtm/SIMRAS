import { describe, expect, it } from "vitest";
import { askAssetAssistant } from "./ai";

const questions = [
  "What is Prakasam Barrage?", "What is its current risk?",
  "Why is the Health Score this value?", "What inspections exist for this asset?",
  "What maintenance is pending?", "What government evidence is available?",
  "What data is missing?", "Explain RUL.",
  "Which assets are high risk?", "How does SIMRAS work?",
];

describe("SIMRAS Gemini advisor orchestration", () => {
  it.each(questions)("sends free-form question and retrieved context to Gemini: %s", async (question) => {
    const result = await askAssetAssistant("AP_DAM_00001", question, [], async (sent, context) => {
      expect(sent).toBe(question);
      expect(context.focus_asset.name).toBe("Prakasam Barrage");
      expect(context.registry_summary.count).toBeGreaterThan(0);
      expect(context).not.toHaveProperty("telemetry");
      expect(context.inspections).toBeInstanceOf(Array);
      return `Model answer for ${question}`;
    });
    expect(result.answer).toBe(`Model answer for ${question}`);
  });

  it("uses an explicitly named asset instead of the selected asset", async () => {
    await askAssetAssistant("AP_DAM_00001", "Describe Andhra Dam", [], async (_, context) => {
      expect(context.focus_asset.name).toBe("Andhra Dam");
      return "Grounded answer";
    });
  });

  it("preserves retrieved evidence during provider failure", async () => {
    const result = await askAssetAssistant("AP_DAM_00001", "Any question", [], async () => {
      throw new Error("provider down");
    });
    expect(result.ai_generated).toBe(false);
    expect(result.answer).toContain('Prakasam Barrage');
    expect(result.answer).toContain('AI-generated interpretation is temporarily unavailable.');
  });
});
