import { describe, expect, it } from 'vitest';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { SimrasDatabase } from './db';
import { RuntimeStore } from './runtimeStore';
import { registerOfficer, authenticateUser } from './auth';
import { parseInfrastructure } from './infrastructure';

describe('persistent officer workflows', () => {
  it('hashes passwords, rejects duplicates, and logs in after reopening storage', async () => {
    const file = path.join(mkdtempSync(path.join(tmpdir(), 'simras-test-')), 'registrations.sqlite3');
    const store = new RuntimeStore(file);
    const database = new SimrasDatabase(store);
    const input = { name: 'Test Engineer', email: ' Engineer.Test ', password: 'Valid-Test-123', confirmPassword: 'Valid-Test-123', role: 'ADMIN' };
    const result = await registerOfficer(input, database);
    expect(result.user.role).toBe('OFFICER');
    expect(result.user.email).toBe('engineer.test');
    expect(JSON.stringify(result)).not.toMatch(/password|\$2[aby]\$/);
    await expect(registerOfficer(input, database)).rejects.toMatchObject({ status: 409 });
    expect(await authenticateUser('engineer.test', 'wrong', database)).toBeNull();
    store.close();
    expect(readFileSync(file).includes(Buffer.from(input.password))).toBe(false);
    const reopened = new RuntimeStore(file);
    expect((await authenticateUser('ENGINEER.TEST', input.password, new SimrasDatabase(reopened)))?.user.name).toBe('Test Engineer');
    reopened.close();
  });

  it('validates passwords and confirmations before creating an account', async () => {
    const database = new SimrasDatabase(new RuntimeStore(':memory:'));
    await expect(registerOfficer({ name: 'Test', email: 'officer2', password: 'short', confirmPassword: 'short' }, database)).rejects.toMatchObject({ status: 400 });
    await expect(registerOfficer({ name: 'Test', email: 'officer2', password: 'LongEnough123', confirmPassword: 'different' }, database)).rejects.toMatchObject({ status: 400 });
    await expect(registerOfficer({ name: 'Test', email: [], password: 'LongEnough123', confirmPassword: 'LongEnough123' }, database)).rejects.toMatchObject({ status: 400 });
  });

  it('rejects concurrent duplicate registration without replacing the first account', async () => {
    const store = new RuntimeStore(':memory:');
    const database = new SimrasDatabase(store);
    const body = { name: 'Concurrent Officer', username: 'same-officer', password: 'Concurrent-123', confirmPassword: 'Concurrent-123' };
    const results = await Promise.allSettled([registerOfficer(body, database), registerOfficer(body, database)]);
    expect(results.filter(result => result.status === 'fulfilled')).toHaveLength(1);
    expect(results.find(result => result.status === 'rejected')).toMatchObject({ reason: { status: 409 } });
    store.close();
  });

  it('persists all infrastructure types and leaves submitted scores unavailable', () => {
    const file = path.join(mkdtempSync(path.join(tmpdir(), 'simras-assets-')), 'registrations.sqlite3');
    const store = new RuntimeStore(file);
    const database = new SimrasDatabase(store);
    const baseline = database.getAssets({}).total;
    const codes = ['bridge', 'dam', 'barrage', 'airport', 'temple'].map(type => {
      const asset = parseInfrastructure({ name: 'New structure', type, latitude: 16.4, longitude: 80.6, health_score: 99, risk_score: 1, rul_years: 100 });
      database.addAsset(asset);
      expect(asset.health_score).toBeNull();
      expect(asset.risk_score).toBeNull();
      expect(asset.rul_years).toBeNull();
      expect(asset.assessment_status).toBe('MODEL_PENDING');
      expect(() => database.addAsset(asset)).toThrow(/already exists/);
      return asset.asset_code;
    });
    store.close();
    const reopened = new RuntimeStore(file);
    const restored = new SimrasDatabase(reopened);
    expect(restored.getAssets({}).total).toBe(baseline + 5);
    for (const code of codes) expect(restored.getAsset(code)?.health_score).toBeNull();
    reopened.close();
  });

  it.each([{}, { latitude: '' }, { latitude: '16bad' }, { latitude: 91 }, { longitude: null }, { type: 'unknown' }, { dimensions: { length_m: -1 } }])('rejects invalid submissions %j', patch => {
    const base = Object.keys(patch).length ? { name: 'Asset', type: 'bridge', latitude: 16, longitude: 80 } : {};
    expect(() => parseInfrastructure({ ...base, ...patch })).toThrow();
  });
});
