import { GoogleGenAI } from "@google/genai";
import { buildAiContext, trimConversationHistory, type ConversationMessage } from "./aiContext";

let aiClient: GoogleGenAI | null = null;

function getAiClient() {
  const key = process.env.GEMINI_API_KEY;
  if (!key || key === "MY_GEMINI_API_KEY") return null;
  aiClient ??= new GoogleGenAI({ apiKey: key });
  return aiClient;
}

function retrieveRelevantEvidence(context: ReturnType<typeof buildAiContext>, prompt: string) {
  const tokens = prompt.toLowerCase().match(/[a-z0-9_]+/g)?.filter((token) => token.length > 2) ?? [];
  const candidates = [
    ["asset_registry", context.asset], ["assessment", context.assessment],
    ["engineering_dimensions", context.engineering_dimensions], ["inspections", context.inspections],
    ["maintenance", context.maintenance], ["telemetry_environment", context.telemetry],
  ] as const;
  const ranked = candidates.map(([name, value]) => ({ name, value, score: tokens.filter((token) => `${name} ${JSON.stringify(value)}`.toLowerCase().includes(token)).length })).sort((a, b) => b.score - a.score);
  const matched = ranked.filter((item) => item.score > 0).slice(0, 3);
  return matched.length ? matched : ranked.slice(0, 2);
}

function unavailableResponse(context: ReturnType<typeof buildAiContext>, prompt: string) {
  return {
    answer: `The Gemini reasoning service is not configured. SIMRAS retrieved available evidence for “${prompt}”, but will not fabricate an engineering conclusion.`,
    key_evidence: retrieveRelevantEvidence(context, prompt).map((item) => ({ section: item.name, data: item.value })),
    data_sources: [context.source.authority, context.source.url].filter(Boolean) as string[],
    limitations: context.missing_evidence.length ? context.missing_evidence.map((item) => `${item}: not currently available in SIMRAS`) : ["External reasoning service unavailable"],
    suggested_next_action: "Configure the backend GEMINI_API_KEY or review the retrieved evidence in the official report.",
    asset_code: context.asset.asset_code,
  };
}

export async function askAssetAssistant(assetCode: string, userPrompt: string, history: ConversationMessage[] = []) {
  const context = buildAiContext(assetCode, userPrompt);
  const client = getAiClient();
  if (!client) return unavailableResponse(context, userPrompt);
  const systemInstruction = `You are the SIMRAS Engineering Advisor. Answer only from supplied SIMRAS evidence. Never invent government data, dimensions, sensor values, inspections, maintenance, scores, or RUL. If evidence is absent say: "That information is not currently available in SIMRAS." Distinguish official, historical, simulated, modelled, and unavailable data. Where useful provide Answer, Key Evidence, Data Source, Limitations, and Suggested Next Action. Never approve records or alter official scores.`;
  const contents = [
    ...trimConversationHistory(history).map((message) => ({ role: message.role === "assistant" ? "model" as const : "user" as const, parts: [{ text: message.content }] })),
    { role: "user" as const, parts: [{ text: `SIMRAS CONTEXT:\n${JSON.stringify(context)}\n\nQUESTION:\n${userPrompt}` }] },
  ];
  try {
    const response = await client.models.generateContent({ model: "gemini-2.5-flash", contents, config: { systemInstruction, temperature: 0.15 } });
    return { answer: response.text || "That information is not currently available in SIMRAS.", key_evidence: retrieveRelevantEvidence(context, userPrompt).map((item) => item.name), data_sources: [context.source.authority, context.source.url].filter(Boolean), limitations: context.missing_evidence, suggested_next_action: "Review linked evidence before an official decision.", asset_code: assetCode };
  } catch {
    return unavailableResponse(context, userPrompt);
  }
}
