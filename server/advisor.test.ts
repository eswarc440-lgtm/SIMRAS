import { beforeEach, describe, expect, it, vi } from 'vitest';
const { generate } = vi.hoisted(() => ({ generate: vi.fn() }));
vi.mock('@google/genai', () => ({ GoogleGenAI: class { models = { generateContent: generate }; } }));
import { askAssetAssistant } from './ai';
import { buildAdvisorDirectory, readAdvisorAssets } from './advisorContext';

describe('system-wide advisor', () => {
  beforeEach(() => { generate.mockReset(); vi.stubEnv('GEMINI_API_KEY', 'test-server-only-key'); });
  it('provides system help and all registered categories without a selected asset', () => {
    const context = buildAdvisorDirectory();
    expect(context.selected_asset_hint).toBeNull();
    expect(context.summary.total).toBeGreaterThanOrEqual(194);
    expect(Object.keys(context.summary.by_type)).toEqual(expect.arrayContaining(['dam', 'barrage', 'bridge', 'airport', 'temple']));
    expect(JSON.stringify(context.system)).toContain('Create Account');
    expect(JSON.stringify(context)).not.toMatch(/password_hash|jwt_secret|test-server-only-key/);
  });
  it('answers system questions with no asset', async () => {
    generate.mockResolvedValue({ text: 'SIMRAS supports infrastructure monitoring, GIS, inspections and maintenance.' });
    const result = await askAssetAssistant(undefined, 'What can SIMRAS do?');
    expect(result.answer).toContain('SIMRAS');
    expect(result.context_assets).toEqual([]);
    expect(result.asset_code).toBeNull();
  });
  it('retrieves a named asset instead of locking the model to the page selection', async () => {
    const call = { name: 'get_asset_evidence', args: { asset_codes: ['AP_DAM_00001'] } };
    generate.mockResolvedValueOnce({ functionCalls: [call], candidates: [{ content: { role: 'model', parts: [{ functionCall: call }] } }] })
      .mockResolvedValueOnce({ text: 'Prakasam Barrage is in the SIMRAS registry.' });
    const result = await askAssetAssistant('AP_DAM_WRIS_AP01MH0072', 'about prakasham');
    expect(result.asset_code).toBe('AP_DAM_00001');
    expect(result.context_assets[0].name).toBe('Prakasam Barrage');
    const toolResponse = generate.mock.calls[1][0].contents.at(-1).parts[0].functionResponse.response;
    expect(toolResponse.assets[0].asset.asset_code).toBe('AP_DAM_00001');
    expect(toolResponse.assets[0].telemetry).toBeNull();
  });
  it('supports comparisons and conversational asset changes', async () => {
    const call = { name: 'get_asset_evidence', args: { asset_codes: ['AP_DAM_00001', 'AP_DAM_NWDP_AP01VH0059'] } };
    generate.mockResolvedValueOnce({ functionCalls: [call], candidates: [{ content: { role: 'model', parts: [{ functionCall: call }] } }] })
      .mockResolvedValueOnce({ text: 'Comparison based on the two asset records.' });
    const result = await askAssetAssistant(undefined, 'Compare it with Srisailam', [{ role: 'user', content: 'about Prakasam' }]);
    expect(result.context_assets.map(asset => asset.asset_code)).toEqual(['AP_DAM_00001', 'AP_DAM_NWDP_AP01VH0059']);
    expect(result.asset_code).toBeNull();
    expect(generate.mock.calls[0][0].contents.some(item => item.parts[0].text === 'about Prakasam')).toBe(true);
  });
  it('validates tool arguments and never reads arbitrary files or other data', () => {
    expect(readAdvisorAssets(['../../.env'], 'question').not_found).toEqual(['../../.env']);
    expect(readAdvisorAssets('AP_DAM_00001', 'question').error).toBeTruthy();
    expect(readAdvisorAssets(Array(9).fill('AP_DAM_00001'), 'question').error).toBeTruthy();
  });
  it('redacts provider errors and terminates repeated tool requests', async () => {
    generate.mockRejectedValueOnce(Object.assign(new Error('secret provider details'), { status: 429 }));
    await expect(askAssetAssistant(undefined, 'What is SIMRAS?')).rejects.toMatchObject({ status: 503 });
    const call = { name: 'get_asset_evidence', args: { asset_codes: ['missing'] } };
    generate.mockResolvedValue({ functionCalls: [call], candidates: [{ content: { role: 'model', parts: [{ functionCall: call }] } }] });
    await expect(askAssetAssistant(undefined, 'Unknown asset')).rejects.toMatchObject({ status: 502 });
    expect(generate).toHaveBeenCalledTimes(5);
  });
});
