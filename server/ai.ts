import { GoogleGenAI } from '@google/genai';
import tls from 'node:tls';
import { buildApplicationAiContext, buildApplicationGlobalAiContext, trimConversationHistory, type ConversationMessage } from './aiContext';

export class AdvisorUnavailableError extends Error {
  constructor(message = 'Gemini request failed', public status: number | null = null, public providerType = 'PROVIDER_ERROR') { super(message); this.name = 'AdvisorUnavailableError'; }
}
export type EvidenceContext = Record<string, any>;
type GenerateAnswer = (
  question: string,
  context: EvidenceContext,
  history: ConversationMessage[],
  user: UserContext
) => Promise<string>;
let providerFailed = false;
export const modelName = () => process.env.GEMINI_MODEL?.trim() || 'gemini-2.5-flash';
export function getAiHealth() {
  const configured = Boolean(process.env.GEMINI_API_KEY?.trim() && process.env.GEMINI_API_KEY !== 'MY_GEMINI_API_KEY');
  return {configured,provider:'gemini',model:modelName(),status:!configured ? 'NOT_CONFIGURED' : providerFailed ? 'ERROR' : 'READY'};
}

export interface UserContext {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string;
}

export type IntentScope = 
  | 'GREETING'
  | 'APPLICATION_GLOBAL'
  | 'ASSET_SPECIFIC'
  | 'INSPECTION'
  | 'MAINTENANCE'
  | 'PREDICTION'
  | 'REPORT'
  | 'GIS'
  | 'DIGITAL_TWIN'
  | 'EVIDENCE'
  | 'WORKFLOW'
  | 'COMPARISON'
  | 'GENERAL_ENGINEERING';

export const systemInstruction = `You are the SIMRAS AI Engineering Advisor and conversational assistant.

You help authenticated SIMRAS users understand infrastructure assets, inspections, maintenance, Health, Risk, RUL, GIS, Digital Twins, reports, workflows, and supporting evidence.

Be conversational and useful.

For greetings, greet the authenticated user by name.

For asset questions, use retrieved SIMRAS evidence.

For general engineering explanations, you may explain concepts from engineering knowledge, but clearly separate general knowledge from asset-specific SIMRAS evidence.

Never invent asset-specific measurements, inspections, maintenance, government records, source documents, Health/Risk/RUL values, or dimensions.

Clearly distinguish verified evidence, validated ML, stored estimates, sparse estimates, and unavailable evidence.

Do not overwhelm users with raw JSON.

Summarize records naturally.

If information is missing, say what is missing.

Answer the actual question first.`;

export function retrievalCounts(context: EvidenceContext) {
  return Object.fromEntries(['inspections','maintenance','environment','government_evidence','source_references','withheld_fields'].map(key => [key,Array.isArray(context[key]) ? context[key].length : 0]));
}

function diagnostic(context: EvidenceContext, status: number | null, providerErrorType: string | null, durationMs?: number) {
  console.info('SIMRAS advisor', {gemini_http_status:status,provider_error_type:providerErrorType,model:modelName(),configured:getAiHealth().configured,asset_code:context.focus_asset?.asset_code,retrieval_counts:retrievalCounts(context),request_duration_ms:durationMs});
}

function classifyIntent(question: string, user: UserContext | null): { scope: IntentScope; isGreeting: boolean; needsUserContext: boolean } {
  const q = question.toLowerCase().trim();
  const greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings'];
  const isGreeting = greetings.some(g => q === g || q.startsWith(g));
  
  if (isGreeting) {
    return { scope: 'GREETING', isGreeting: true, needsUserContext: true };
  }
  
  // Identity questions
  if (q.includes('who am i') || q.includes('my name') || q.includes('my role')) {
    return { scope: 'GREETING', isGreeting: false, needsUserContext: true };
  }
  
  // Application-wide questions
  if (q.includes('how many') && (q.includes('asset') || q.includes('dam') || q.includes('bridge') || q.includes('barrage') || q.includes('airport') || q.includes('temple'))) {
    return { scope: 'APPLICATION_GLOBAL', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('what is simras') || q.includes('how does simras work') || q.includes('simras modules') || q.includes('simras workflow')) {
    return { scope: 'WORKFLOW', isGreeting: false, needsUserContext: false };
  }
  
  // Asset-specific keywords
  if (q.includes('inspection') || q.includes('inspect')) {
    return { scope: 'INSPECTION', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('maintenance') || q.includes('repair') || q.includes('fix')) {
    return { scope: 'MAINTENANCE', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('health') || q.includes('risk') || q.includes('rul') || q.includes('remaining useful life')) {
    return { scope: 'PREDICTION', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('report') || q.includes('assessment')) {
    return { scope: 'REPORT', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('gis') || q.includes('location') || q.includes('district') || q.includes('coordinates') || q.includes('map')) {
    return { scope: 'GIS', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('digital twin') || q.includes('3d') || q.includes('dimension') || q.includes('geometry')) {
    return { scope: 'DIGITAL_TWIN', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('evidence') || q.includes('source') || q.includes('document') || q.includes('government')) {
    return { scope: 'EVIDENCE', isGreeting: false, needsUserContext: false };
  }
  
  if (q.includes('compare') || q.includes('versus') || q.includes('vs')) {
    return { scope: 'COMPARISON', isGreeting: false, needsUserContext: false };
  }
  
  // General engineering concepts
  if (q.includes('what is') && (q.includes('scour') || q.includes('cavitation') || q.includes('corrosion') || q.includes('fatigue') || q.includes('settlement'))) {
    return { scope: 'GENERAL_ENGINEERING', isGreeting: false, needsUserContext: false };
  }
  
  // Default to asset-specific if it mentions an asset name, otherwise global
  return { scope: 'APPLICATION_GLOBAL', isGreeting: false, needsUserContext: false };
}

function enhanceContextWithUser(context: EvidenceContext, user: UserContext | null): EvidenceContext {
  if (!user) return context;
  return {
    ...context,
    authenticated_user: {
      name: user.name,
      role: user.role,
      department: user.department,
    },
  };
}

async function generateWithGemini(question: string, context: EvidenceContext, history: ConversationMessage[], user: UserContext | null, maxRetries = 2): Promise<string> {
  if (!getAiHealth().configured) throw new AdvisorUnavailableError('GEMINI_API_KEY is not configured on the server.',null,'NOT_CONFIGURED');
  
  if (process.platform === 'win32' && typeof tls.setDefaultCACertificates === 'function') {
    tls.setDefaultCACertificates([...tls.getCACertificates('default'),...tls.getCACertificates('system')]);
  }
  
  const ai = new GoogleGenAI({apiKey:process.env.GEMINI_API_KEY});
  const enhancedContext = enhanceContextWithUser(context, user);
  
  const contents = [
    ...trimConversationHistory(history).map(message => ({role:message.role === 'assistant' ? 'model' as const : 'user' as const,parts:[{text:message.content.slice(0,4000)}]})),
    {role:'user' as const,parts:[{text:`SIMRAS evidence:\n${JSON.stringify(enhancedContext)}\n\nQuestion: ${question}`}]},
  ];
  
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const startTime = Date.now();
    try {
      const response = await ai.models.generateContent({
        model:modelName(),
        contents,
        config:{systemInstruction,temperature:0.1,httpOptions:{timeout:45000}}
      });
      
      if (!response.text?.trim()) throw new AdvisorUnavailableError('Gemini returned no text',200,'EMPTY_RESPONSE');
      
      providerFailed = false;
      const duration = Date.now() - startTime;
      diagnostic(enhancedContext,200,null,duration);
      return response.text.trim();
      
    } catch (error) {
      lastError = error as Error;
      const status = typeof (error as any).status === 'number' ? (error as any).status : null;
      const duration = Date.now() - startTime;
      
      // Retry on rate limit (429) or transient server errors (5xx)
      const shouldRetry = (status === 429 || (status && status >= 500)) && attempt < maxRetries;
      
      if (shouldRetry) {
        const delayMs = Math.pow(2, attempt) * 1000; // Exponential backoff: 1s, 2s, 4s
        console.warn(`Gemini request failed (status ${status}), retrying in ${delayMs}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
        await new Promise(resolve => setTimeout(resolve, delayMs));
        continue;
      }
      
      providerFailed = true;
      diagnostic(enhancedContext,status,status === 429 ? 'RATE_LIMIT' : status ? 'HTTP_ERROR' : 'TRANSPORT_ERROR',duration);
      throw new AdvisorUnavailableError(
        'Gemini generation failed',
        status,
        error instanceof AdvisorUnavailableError ? error.providerType : status === 429 ? 'RATE_LIMIT' : status ? 'HTTP_ERROR' : 'TRANSPORT_ERROR'
      );
    }
  }
  
  throw lastError || new AdvisorUnavailableError('Gemini generation failed after retries');
}
function generateLocalGreeting(user: UserContext | null): string {
  if (user) {
    return `Hello, ${user.name}! I'm the SIMRAS AI Engineering Advisor. I can help you with infrastructure assets, inspections, maintenance records, Health and Risk assessments, RUL, GIS information, Digital Twins, reports, and available evidence. What would you like to inspect?`;
  }
  return 'Hello! I\'m the SIMRAS AI Engineering Advisor. I can help you with infrastructure assets, inspections, maintenance records, Health and Risk assessments, RUL, GIS information, Digital Twins, reports, and available evidence. What would you like to inspect?';
}

export function evidenceSummary(context: EvidenceContext, user: UserContext | null, intent: IntentScope) {
  // For greetings, use a friendly local response instead of dumping evidence
  if (intent === 'GREETING') {
    return generateLocalGreeting(user);
  }
  
  const asset = context.focus_asset;
  const lines = [`SIMRAS evidence summary: ${asset?.name ?? 'Application-wide'} (${asset?.asset_code ?? 'GLOBAL'})`];
  
  if (asset) {
    lines.push(`Category: ${asset.asset_type ?? asset.category ?? 'unavailable'}; district: ${asset.district ?? 'unavailable'}.`);
    for (const [key,field] of [['health','health_score'],['risk','risk_score'],['rul','rul_years']]) {
      const assessment = context.assessments?.[key];
      const valid = assessment?.value != null && !['WITHHELD','ASSESSMENT_ERROR','NO_EVIDENCE'].includes(assessment.status);
      const stored = assessment?.stored_unverified_value ?? asset[field];
      lines.push(valid ? `${key}: ${assessment.value} (${assessment.status}; ${assessment.method ?? assessment.model_version ?? 'method unavailable'}).` : `${key}: WITHHELD as a current validated assessment.${stored != null ? ` Stored/unverified value: ${stored}.` : ''} ${assessment?.reason ?? 'Sufficient assessment evidence is unavailable.'}`);
    }
    if (asset.assessment_basis) lines.push(`Stored basis (unverified): ${asset.assessment_basis}`);
  }
  
  for (const key of ['inspections','maintenance']) {
    const rows = context[key] ?? [];
    lines.push(`${key}: ${rows.length} retrieved record(s).`);
    for (const row of rows.slice(0,5)) lines.push(JSON.stringify(row));
  }
  
  if (context.provenance) lines.push(`Provenance: ${typeof context.provenance === 'string' ? context.provenance : JSON.stringify(context.provenance)}`);
  if (context.source_references?.length) lines.push(`Sources: ${context.source_references.map((r:any) => typeof r === 'string' ? r : JSON.stringify(r)).join('; ')}`);
  if (context.missing_evidence?.length) lines.push(`Unavailable evidence: ${context.missing_evidence.join(', ')}.`);
  lines.push('AI-generated interpretation is temporarily unavailable.');
  return lines.join('\n\n');
}
export async function askAssetAssistant(
  assetCode:string,
  userPrompt:string,
  history:ConversationMessage[] = [],
  generate:GenerateAnswer = generateWithGemini,
  retrieve:(code:string,question:string)=>EvidenceContext|Promise<EvidenceContext> = buildApplicationAiContext,
  user: UserContext | null = null
) {
  const prompt = userPrompt.trim();
  if (!prompt || prompt.length > 4000) throw new Error('Prompt must contain between 1 and 4000 characters');
  
  const intent = classifyIntent(prompt, user);
  const context = await retrieve(assetCode,prompt);
  
  let answer: string;
  let aiGenerated = true;
  let providerError: {type:string;http_status:number|null}|null = null;
  
  try {
    answer = await generate(prompt,context,history,user);
  } catch (error) {
    const e = error as AdvisorUnavailableError;
    providerError = {type:e.providerType ?? 'PROVIDER_ERROR',http_status:typeof e.status === 'number' ? e.status : null};
    diagnostic(context,providerError.http_status,providerError.type);
    answer = evidenceSummary(context,user,intent.scope);
    aiGenerated = false;
  }
  
  return {
    answer,
    asset_code:context.focus_asset.asset_code,
    ai_generated:aiGenerated,
    provider_error:providerError,
    data_sources:context.source_references ?? [],
    limitations:context.missing_evidence ?? [],
    evidence:context,
    scope: intent.scope,
  };
}

// -----------------------------------------------------------------------------
// Application-wide Gemini advisor.
// Asset-specific questions continue to use askAssetAssistant.
// -----------------------------------------------------------------------------
function globalEvidenceSummary(context: EvidenceContext, user: UserContext | null, intent: IntentScope) {
  // For greetings, use a friendly local response instead of dumping evidence
  if (intent === 'GREETING') {
    return generateLocalGreeting(user);
  }
  
  const application = context.application ?? {};

  return [
    "SIMRAS application evidence summary",
    `Registered assets: ${application.total_assets ?? "unavailable"}.`,
    `Inspection records: ${application.total_inspections ?? "unavailable"}.`,
    `Maintenance records: ${application.total_maintenance ?? "unavailable"}.`,
    `High-risk stored records: ${application.high_risk_assets ?? "unavailable"}.`,
    context.provenance ? `Provenance: ${context.provenance}` : "",
    "AI-generated interpretation is temporarily unavailable.",
  ].filter(Boolean).join("\n\n");
}

export async function askGlobalAssistant(
  userPrompt: string,
  history: ConversationMessage[] = [],
  generate: GenerateAnswer = generateWithGemini,
  retrieve: (question: string) => EvidenceContext | Promise<EvidenceContext> =
    buildApplicationGlobalAiContext,
  user: UserContext | null = null,
) {
  const prompt = String(userPrompt ?? "").trim();

  if (!prompt || prompt.length > 4000) {
    throw new Error("Prompt must contain between 1 and 4000 characters");
  }

  const intent = classifyIntent(prompt, user);
  const context = await retrieve(prompt);

  let answer: string;
  let aiGenerated = true;
  let providerError: { type: string; http_status: number | null } | null = null;

  try {
    answer = await generate(prompt, context, history, user);
  } catch (error) {
    const e = error as AdvisorUnavailableError;

    providerError = {
      type: e.providerType ?? "PROVIDER_ERROR",
      http_status: typeof e.status === "number" ? e.status : null,
    };

    diagnostic(context, providerError.http_status, providerError.type);

    answer = globalEvidenceSummary(context, user, intent.scope);
    aiGenerated = false;
  }

  return {
    answer,
    asset_code: context.focus_asset?.asset_code ?? null,
    scope: context.scope ?? intent.scope,
    ai_generated: aiGenerated,
    provider_error: providerError,
    data_sources: context.source_references ?? [],
    limitations: context.missing_evidence ?? [],
    evidence: context,
  };
}
