import assert from 'node:assert/strict';
import fs from 'node:fs';
const base = process.env.SIMRAS_TEST_URL || 'http://127.0.0.1:3100';
const login = await fetch(base + '/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'officer@simras.gov.in', password: 'Officer@123' }) });
assert.equal(login.status, 200);
const { token } = await login.json();
const history = [];
const results = [];
async function ask(question, selected, continuing = true) {
  const response = await fetch(base + '/api/v1/ai/ask', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ question, selected_asset_code: selected, history: continuing ? history : [] }) });
  const body = await response.json();
  assert.equal(response.status, 200, body.error);
  assert.ok(body.answer?.length > 20);
  assert.ok(!body.answer.includes('The current context is for the Andhra Dam'));
  if (continuing) history.push({ role: 'user', content: question }, { role: 'assistant', content: body.answer });
  results.push({ question, ...body });
  console.log(JSON.stringify({ question, assets: body.context_assets.map(asset => asset.name), answer: body.answer.slice(0, 350) }));
  return body;
}
const system = await ask('What is SIMRAS and how do I create an account and add infrastructure? Answer briefly.', undefined, false);
assert.match(system.answer, /Create Account/i);
assert.match(system.answer, /Add Infrastructure/i);
const prak = await ask('about prakasham', 'AP_DAM_WRIS_AP01MH0072');
assert.ok(prak.context_assets.some(asset => asset.asset_code === 'AP_DAM_00001'));
let srisailam = await ask('srisailam', 'AP_DAM_WRIS_AP01MH0072');
if (!srisailam.context_assets.length) {
  assert.match(srisailam.answer, /temple/i);
  assert.match(srisailam.answer, /project|dam/i);
  srisailam = await ask('Srisailam Project, the dam', 'AP_DAM_WRIS_AP01MH0072');
}
assert.ok(srisailam.context_assets.some(asset => asset.asset_code === 'AP_DAM_NWDP_AP01VH0059'));
const followup = await ask('What is its risk and RUL? Briefly distinguish estimates from measurements.', 'AP_DAM_WRIS_AP01MH0072');
assert.ok(followup.context_assets.some(asset => asset.asset_code === 'AP_DAM_NWDP_AP01VH0059'));
const comparison = await ask('Compare Prakasam Barrage and Srisailam Project. Use the recorded dimensions and distinguish estimates.', undefined);
assert.ok(comparison.context_assets.some(asset => asset.asset_code === 'AP_DAM_00001'));
assert.ok(comparison.context_assets.some(asset => asset.asset_code === 'AP_DAM_NWDP_AP01VH0059'));
const inventory = await ask('How many assets does SIMRAS have, broken down by type?', undefined, false);
const health = await (await fetch(base + '/api/v1/health')).json();
assert.ok(inventory.answer.includes(String(health.asset_count)));
fs.writeFileSync('safety_backup_20260927_global_advisor/live-advisor-results.json', JSON.stringify(results, null, 2));
console.log('PASS: system help, spelling variant, asset switching, follow-up, comparison and live inventory');
