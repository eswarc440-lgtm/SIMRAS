import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import dotenv from 'dotenv';

const base = process.env.SIMRAS_TEST_URL || 'http://127.0.0.1:3100';
const statePath = path.join(os.tmpdir(), 'simras-officer-verification-state.json');
const request = async (url, body, token) => {
  const response = await fetch(base + url, { method: body === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  return { status: response.status, data: await response.json() };
};
let state;
if (process.argv.includes('--restart-check')) {
  state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
} else {
  const password = 'Verification-only-123';
  const email = `verify-${Date.now()}@example.test`;
  const registration = await request('/api/auth/register', { name: 'Verification Engineer', email, password, confirmPassword: password });
  assert.equal(registration.status, 201);
  assert.equal(registration.data.user.role, 'OFFICER');
  assert.ok(!/password|\$2[aby]\$/.test(JSON.stringify(registration.data)));
  const duplicate = await request('/api/auth/register', { name: 'Duplicate', email: email.toUpperCase(), password, confirmPassword: password });
  assert.equal(duplicate.status, 409);
  assert.equal((await request('/api/auth/login', { email, password: 'wrong-password' })).status, 401);
  const login = await request('/api/auth/login', { email, password });
  assert.equal(login.status, 200);
  const created = await request('/api/v1/infrastructure', { name: 'Verification Pending Bridge', type: 'bridge', latitude: 16.5, longitude: 80.6, dimensions: { length_m: 100.5 }, health_score: 99, rul_years: 80 }, login.data.token);
  assert.equal(created.status, 201);
  state = { email, password, code: created.data.asset_code };
  fs.writeFileSync(statePath, JSON.stringify(state));
  assert.equal((await request('/api/v1/infrastructure', { name: 'Invalid', type: 'bridge', latitude: null, longitude: 80.6 }, login.data.token)).status, 400);
  assert.equal((await request('/api/v1/infrastructure', { name: 'Unauthorized', type: 'bridge', latitude: 16.5, longitude: 80.6 })).status, 403);
  assert.equal((await request('/api/v1/ai/assets/missing/ask', { question: 'Explain' }, login.data.token)).status, 404);
  assert.equal((await request(`/api/v1/ai/assets/${state.code}/ask`, { question: '' }, login.data.token)).status, 400);
  const advisor = await request('/api/v1/ai/assets/AP_BR_00002/ask', { question: 'Briefly identify this bridge and explain its Health, Risk, RUL and current inspection evidence. Distinguish registry scores, model estimates and unavailable evidence.' }, login.data.token);
  assert.equal(advisor.status, 200, advisor.data.error);
  assert.equal(advisor.data.asset_code, 'AP_BR_00002');
  assert.ok(advisor.data.answer.length > 100);
  console.log('Gemini selected-asset answer:', advisor.data.answer);
  dotenv.config({ path: ['.env.local', '.env'], quiet: true });
  const key = process.env.GEMINI_API_KEY;
  for (const file of fs.readdirSync('dist/assets')) {
    if (/\.(js|css|map)$/.test(file)) {
      const text = fs.readFileSync(path.join('dist/assets', file), 'utf8');
      assert.ok(!text.includes('GEMINI_API_KEY'));
      if (key) assert.ok(!text.includes(key));
    }
  }
  for (const url of ['/data/runtime/registrations.sqlite3', '/data/runtime/registrations.sqlite3-wal', '/server.cjs', '/server.cjs.map', '/.env']) {
    assert.notEqual((await fetch(base + url)).status, 200, url);
  }
  assert.equal((await fetch(base + '/images/ap-government-emblem.png')).status, 200);
}
const login = await request('/api/auth/login', { email: state.email, password: state.password });
assert.equal(login.status, 200);
for (const url of [`/api/v1/assets/${state.code}`, `/api/v1/infrastructure/${state.code}`, `/api/v1/predictions/${state.code}`]) {
  const asset = (await request(url)).data;
  assert.equal(asset.health_score, null, url);
  assert.equal(asset.risk_score, null, url);
  assert.equal(asset.rul_years, null, url);
}
const twin = (await request(`/api/v1/assets/${state.code}/twin`)).data;
assert.equal(twin.ai.health_score, null);
assert.equal(twin.ai.remaining_life_years, null);
const report = (await request(`/api/v1/assets/${state.code}/reports/real`)).data;
assert.equal(report.assessment.health_score, null);
assert.equal(report.multi_variable_prediction.predicted_health_score, null);
const map = (await request('/api/v1/map/features')).data;
assert.ok(map.features.some(feature => feature.properties.asset_code === state.code));
const assets = (await request('/api/v1/assets?limit=1000')).data.items;
const original = JSON.parse(fs.readFileSync('data/canonical_assets_194.json', 'utf8'));
for (const asset of original) assert.ok(assets.some(item => item.asset_code === asset.asset_code), asset.asset_code);
for (const type of ['bridge', 'dam', 'barrage', 'airport', 'temple']) assert.ok(assets.some(item => item.asset_type === type));
console.log(JSON.stringify({ result: 'PASS', restarted: process.argv.includes('--restart-check'), originalAssetsPreserved: original.length, createdAsset: state.code, persistentLogin: true, pendingScores: true, GISRetrieval: true }));
