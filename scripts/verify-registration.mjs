// Local production HTTP verification using isolated credentials and storage.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import net from 'node:net';
import { randomBytes } from 'node:crypto';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import 'dotenv/config';

const liveAi = process.argv.includes('--live-ai');

const directory = await mkdtemp(path.join(tmpdir(), 'simras-http-'));
const secret = randomBytes(48).toString('hex');
const roles = ['public', 'officer', 'reviewer', 'admin'];
const passwords = Object.fromEntries(roles.map(role => [role, randomBytes(24).toString('hex')]));
const hashes = Object.fromEntries(roles.map(role => [`${role}@simras.gov.in`, bcrypt.hashSync(passwords[role], 4)]));
const listener = net.createServer();
listener.listen(0, '127.0.0.1');
await once(listener, 'listening');
const port = listener.address().port;
await new Promise(resolve => listener.close(resolve));
const base = `http://127.0.0.1:${port}`;
let server;
let log = '';

async function start() {
  log = '';
  server = spawn(process.execPath, ['dist/server.cjs'], {
    cwd: process.cwd(), windowsHide: true,
    env: {...process.env, NODE_ENV:'production', PORT:String(port),
      JWT_SECRET:secret, SIMRAS_ACCOUNT_PASSWORD_HASHES:JSON.stringify(hashes),
      SIMRAS_DATA_DIR:directory, SIMRAS_BACKEND_URL:'', GEMINI_API_KEY:liveAi ? process.env.GEMINI_API_KEY ?? '' : ''},
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stdout.on('data', chunk => { log += chunk; });
  server.stderr.on('data', chunk => { log += chunk; });
  for (let attempt = 0; attempt < 80; attempt++) {
    if (server.exitCode !== null) throw new Error(`Server exited: ${log}`);
    try { if ((await fetch(`${base}/health`)).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Server did not start: ${log}`);
}
async function stop() {
  if (server && server.exitCode === null) {
    const exited = once(server, 'exit');
    server.kill();
    await exited;
  }
}
async function request(route, {method='GET', token, body, status=200} = {}) {
  const response = await fetch(base + route, {method,
    headers: {...(token ? {Authorization:`Bearer ${token}`} : {}), ...(body ? {'Content-Type':'application/json'} : {})},
    ...(body ? {body:JSON.stringify(body)} : {}), signal:AbortSignal.timeout(liveAi ? 60000 : 10000)});
  assert.equal(response.status, status, `${method} ${route}`);
  return response.json();
}

try {
  await start();
  const tokens = {};
  for (const role of roles) {
    const login = await request('/api/v1/auth/login', {method:'POST', body:{email:`${role}@simras.gov.in`, password:passwords[role]}});
    tokens[role] = login.token;
  }
  await request('/api/v1/auth/login', {method:'POST', body:{email:'admin@simras.gov.in',password:'Admin@123'},status:401});
  const expired = jwt.sign({id:'usr-officer',email:'officer@simras.gov.in'}, secret, {expiresIn:-1});
  for (const token of [undefined, 'tampered', expired]) await request('/api/v1/auth/me', {token,status:401});
  const asset = {name:'HTTP Verification Bridge',asset_type:'bridge',district:'Krishna',latitude:16.5,longitude:80.5};
  for (const [role,status] of [['public',403],['reviewer',403]]) {
    await request('/api/v1/assets',{method:'POST',token:tokens[role],body:asset,status});
  }
  await request('/api/v1/assets',{method:'POST',body:asset,status:401});
  const created = await request('/api/v1/assets',{method:'POST',token:tokens.officer,body:{...asset,created_by:'usr-admin',health_score:99},status:201});
  assert.equal(created.status,'PENDING_REVIEW');
  assert.equal(created.created_by,'usr-officer');
  assert.equal(created.health_score,null);
  const code = created.asset_code;
  assert.equal((await request(`/api/v1/assets?search=${code}`)).total,0);
  for (const route of [`/api/v1/assets/${code}`,`/api/v1/assets/${code}/twin`,`/api/v1/gis/assets/${code}`,`/api/v1/reports/assets/${code}/assessment`]) {
    await request(route,{status:404});
  }
  await request(`/api/v1/assets/${code}/observations`, {method:'POST',
    body:{reporter_name:'Verification',observation_type:'WATER_OVERFLOW',description:'Private registration must not be published'},status:404});
  const pendingAdmin = await request('/api/v1/assets',{method:'POST',token:tokens.admin,body:{...asset,name:'Admin pending verification'},status:201});
  await request(`/api/v1/registrations/${pendingAdmin.asset_code}`,{method:'PATCH',token:tokens.admin,body:{status:'APPROVED',comments:'Self review'},status:403});
  await request(`/api/v1/registrations/${code}`,{method:'PATCH',token:tokens.officer,body:{status:'APPROVED',comments:'Officer review'},status:403});
  const reviewed = await request(`/api/v1/registrations/${code}`,{method:'PATCH',token:tokens.reviewer,body:{status:'APPROVED',comments:'Identity reviewed'}});
  assert.equal(reviewed.health_score,null);
  assert.equal((await request(`/api/v1/assets/${code}/twin`)).ai.health_score,null);
  assert.equal((await request(`/api/v1/predictions/${code}`)).health_score,null);
  assert.equal((await request(`/api/v1/infrastructure/${code}`)).health_score,null);
  assert.equal((await request(`/api/v1/assets/${code}/assessment`)).status,'WITHHELD');
  for (const assetType of ['dam','barrage']) {
    const hydraulic = await request('/api/v1/assets',{method:'POST',token:tokens.officer,
      body:{...asset,name:`Unassessed ${assetType}`,asset_type:assetType},status:201});
    await request(`/api/v1/registrations/${hydraulic.asset_code}`,{method:'PATCH',token:tokens.reviewer,
      body:{status:'APPROVED',comments:'Identity reviewed; no forecast evidence'}});
    const forecast = await request(`/api/v1/assets/${hydraulic.asset_code}/operational-forecast`);
    assert.equal(forecast.status,'WITHHELD');
    assert.equal(forecast.predicted_level_m,null);
    assert.equal(forecast.predicted_storage_mcm,null);
  }
  assert.equal((await request('/api/v1/notifications',{token:tokens.officer})).some(item => item.asset_code === code),false);
  assert.ok((await request('/api/v1/notifications/unread-count',{token:tokens.reviewer})).count >= 2);
  const answer = await request('/api/v1/ai/assets/AP_DAM_00001/ask',{method:'POST',token:tokens.officer,body:{prompt:'Explain Andhra Dam health score'}});
  assert.equal(answer.asset_code,'AP_DAM_WRIS_AP01MH0072');
  assert.equal(answer.ai_generated,liveAi, `Advisor did not use expected provider: ${JSON.stringify(answer.provider_error)}`);
  assert.ok(answer.answer.length > 20);
  if (!liveAi) assert.ok(answer.answer.includes('unverified'));
  if (liveAi) {
    const prakasam = await request('/api/v1/ai/assets/AP_DAM_00001/ask',{method:'POST',token:tokens.officer,
      body:{prompt:'Explain what is known and withheld about Prakasam Barrage remaining useful life.'}});
    assert.equal(prakasam.ai_generated,true,JSON.stringify(prakasam.provider_error));
    assert.match(prakasam.evidence.focus_asset.name,/Prakasam/i);
    console.log('PASS: live Gemini answers for Andhra Dam and Prakasam Barrage through the production HTTP gateway.');
  }
  await stop();
  await start();
  const persisted = await request('/api/v1/registrations',{token:tokens.reviewer});
  assert.equal(persisted.find(item => item.asset_code === code).status,'VERIFIED');
  assert.equal(persisted.find(item => item.asset_code === pendingAdmin.asset_code).status,'PENDING_REVIEW');
  assert.equal((await request(`/api/v1/assets?search=${code}`)).total,1);
  assert.ok((await request('/api/v1/notifications',{token:tokens.reviewer})).some(item => item.asset_code === code));
  console.log('PASS: production login, role matrix, token rejection, private submissions, self-review prevention, WITHHELD projections, advisor fallback, and persistence across process restart.');
} finally {
  await stop();
  if (path.dirname(directory) !== path.resolve(tmpdir()) || !path.basename(directory).startsWith('simras-http-')) throw new Error('Unexpected verification directory');
  await rm(directory,{recursive:true,force:true});
}
