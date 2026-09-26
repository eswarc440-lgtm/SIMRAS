import { afterEach, describe, expect, it, vi } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { askAssetAssistant, getAiHealth } from './ai';
import { authenticateUser, normalizeRole, resolveAuthenticatedUser } from './auth';
import bcrypt from 'bcryptjs';
import { RegistrationStore } from './registrationStore';
import { resolveAsset } from './aiContext';
import { db } from './db';
import { generateAssetReportJson, generateAssetReportCsv } from './reports';

afterEach(() => vi.unstubAllEnvs());
describe('advisor repair', () => {
  it('health exposes only safe fields and detects missing key', () => {
    vi.stubEnv('GEMINI_API_KEY', '');
    expect(getAiHealth()).toEqual({configured:false,provider:'gemini',model:'gemini-2.5-flash',status:'NOT_CONFIGURED'});
  });
  it('retains stored Andhra evidence when Gemini fails', async () => {
    const answer = await askAssetAssistant('AP_DAM_WRIS_AP01MH0072', 'Explain health score', [], async () => { throw Object.assign(new Error('secret provider detail'), {status:503}); });
    expect(answer.answer).toContain('59.9');
    expect(answer.answer).toContain('AI-generated interpretation is temporarily unavailable.');
    expect(answer.answer).toContain('unverified');
    expect(answer.answer).not.toContain('secret provider detail');
    expect(answer.ai_generated).toBe(false);
  });
  it('does not guess between duplicate canonical names', () => {
    const records = [{asset_code:'A',name:'Prakasam Barrage'}, {asset_code:'B',name:'Prakasam Barrage'}];
    expect(() => resolveAsset(records, 'A', 'Prakasam Barrage')).toThrow('Multiple assets');
  });
});
describe('server authorization', () => {
  it('rejects demo credentials in production and accepts only configured password hashes', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('SIMRAS_ACCOUNT_PASSWORD_HASHES', '');
    expect(authenticateUser('admin@simras.gov.in', 'Admin@123')).toBeNull();
    vi.stubEnv('SIMRAS_ACCOUNT_PASSWORD_HASHES', JSON.stringify({
      'admin@simras.gov.in': bcrypt.hashSync('isolated-test-password', 4),
    }));
    expect(authenticateUser('admin@simras.gov.in', 'Admin@123')).toBeNull();
    expect(authenticateUser('admin@simras.gov.in', 'isolated-test-password')?.user.role).toBe('ADMIN');
    expect(authenticateUser('officer@simras.gov.in', 'Officer@123')).toBeNull();
  });
  it('normalizes known roles and fails closed for unknown roles', () => {
    expect(normalizeRole(' officer ')).toBe('OFFICER');
    expect(normalizeRole('superuser')).toBe('PUBLIC');
  });
  it('gets role from server user rather than token claims', () => {
    expect(resolveAuthenticatedUser({id:'usr-public',email:'public@simras.gov.in',role:'ADMIN'})?.role).toBe('PUBLIC');
    expect(resolveAuthenticatedUser({id:'invalid',email:'officer@simras.gov.in'})).toBeNull();
  });
});
describe('persistent registration', () => {
  it('persists pending asset and notification after reopening, rejects self review', () => {
    const directory = mkdtempSync(path.join(tmpdir(),'simras-test-'));
    const file = path.join(directory,'registrations.sqlite3');
    let store = new RegistrationStore(file);
    try {
      store.create({asset_code:'TEST',name:'Test asset',created_by:'officer',status:'PENDING_REVIEW',health_score:null});
      store.close();
      store = new RegistrationStore(file);
      expect(store.list()[0].status).toBe('PENDING_REVIEW');
      expect(store.notifications()).toHaveLength(1);
      expect(() => store.review('TEST',{id:'officer',role:'ADMIN'},'APPROVED','Checked')).toThrow('own');
      expect(() => store.review('TEST',{id:'someone',role:'OFFICER'},'APPROVED','Checked')).toThrow('Reviewer or Admin');
      expect(store.review('TEST',{id:'reviewer',role:'REVIEWER'},'APPROVED','Checked').health_score).toBeNull();
    } finally { store.close(); rmSync(directory,{recursive:true,force:true}); }
  });
});

describe('registration visibility', () => {
  it('keeps approved registration reports withheld without invented projections', () => {
    const code = `AP_BR_TEST_${crypto.randomUUID().slice(0, 8)}`;
    db.addAsset({asset_code:code,name:'Unassessed Crossing',asset_type:'bridge',district:'Krishna',
      status:'PENDING_REVIEW',identity_status:'PENDING_VERIFICATION',created_by:'usr-officer',
      assessment_status:'WITHHELD',health_score:null,risk_score:null,rul_years:null,risk_level:null} as any);
    expect(() => generateAssetReportJson(code)).toThrow('not found');
    db.reviewRegistration(code, db.getUser('reviewer@simras.gov.in')!, 'APPROVED', 'Identity reviewed');
    const report = generateAssetReportJson(code);
    expect(report.assessment.health_score).toBeNull();
    expect(report.multi_variable_prediction).toBeNull();
    expect(report.environmental_time_series).toEqual([]);
    expect(report.seven_day_forecast).toEqual([]);
    expect(generateAssetReportCsv(code)).toContain('WITHHELD');
  });
  it('keeps a pending submission in the review queue but out of public registry and search', () => {
    const code = `AP_BR_TEST_${crypto.randomUUID().slice(0, 8)}`;
    db.addAsset({asset_code:code,name:'Pending Test Crossing',asset_type:'bridge',district:'Krishna',
      status:'PENDING_REVIEW',identity_status:'PENDING_VERIFICATION',created_by:'usr-officer',
      health_score:null,risk_score:null,rul_years:null,risk_level:null} as any);
    expect(db.getRegistrations().some(asset => asset.asset_code === code)).toBe(true);
    expect(db.getAssets({search:code}).items).toHaveLength(0);
    expect(db.search(code).assets).toHaveLength(0);
    expect(db.getPublicAsset(code)).toBeUndefined();
  });

  it('shows registration notifications only to reviewers and admins', () => {
    const code = `AP_BR_TEST_${crypto.randomUUID().slice(0, 8)}`;
    db.addAsset({asset_code:code,name:'Private Review Test',asset_type:'bridge',district:'Krishna',
      status:'PENDING_REVIEW',identity_status:'PENDING_VERIFICATION',created_by:'usr-officer',
      health_score:null,risk_score:null,rul_years:null,risk_level:null} as any);
    expect(db.getNotifications('OFFICER').some(item => item.asset_code === code)).toBe(false);
    expect(db.getNotifications('REVIEWER').some(item => item.asset_code === code)).toBe(true);
  });
});
