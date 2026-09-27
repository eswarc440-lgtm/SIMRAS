import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { randomUUID } from 'node:crypto';
import { db, type SimrasDatabase, type UserRecord } from './db';
import { RequestError } from './infrastructure';

// Preserve existing sandbox logins using bcrypt verification.
const seedHashes: Record<string, string> = {
  'admin@simras.gov.in': '$2b$12$rzTaE99cEERSpl6ZOBasR.N2NIQYEqf/OI4Mk9h0MKh.9Do9BBqGK',
  'officer@simras.gov.in': '$2b$12$4Gx83.fyfEDzL7BdCNIp.u4hVCw2BrOrqX9SRWjspSIfiSGdNLwRa',
  'reviewer@simras.gov.in': '$2b$12$tDH7DOPJ9Ybd0vccA.mL9uOVkmBTwXIjoL9lj5ybdjdu7Y9HuieNO',
  'public@simras.gov.in': '$2b$12$uxivK4/fPQNeEO8QXMOB4.ugbVYFreIAJqfgaD3/Dk.AtmcYgEh0S',
};
function signingSecret(database = db) { return process.env.JWT_SECRET || database.runtime.signingSecret(); }
export function generateToken(user: UserRecord, database = db): string {
  const { id, email, name, role, department } = user;
  return jwt.sign({ id, email, name, role, department }, signingSecret(database), { expiresIn: '24h', algorithm: 'HS256' });
}
export function verifyToken(token: string): any {
  try { return jwt.verify(token, signingSecret(), { algorithms: ['HS256'] }); } catch { return null; }
}
export async function authenticateUser(identifier: unknown, password: unknown, database: SimrasDatabase = db) {
  if (typeof identifier !== 'string' || typeof password !== 'string' || Buffer.byteLength(password, 'utf8') > 72) return null;
  const normalized = identifier.trim().toLowerCase();
  const account = database.runtime.account(normalized);
  const user = account?.user ?? database.getUser(normalized);
  const hash = account?.hash ?? seedHashes[normalized];
  const valid = await bcrypt.compare(password, hash ?? seedHashes['officer@simras.gov.in']);
  if (!user || !hash || !valid) return null;
  return { user, token: generateToken(user, database) };
}
export async function registerOfficer(body: any, database: SimrasDatabase = db) {
  const { name, password, confirmPassword, confirm_password } = body ?? {};
  const identifier = body?.email ?? body?.username;
  if (typeof name !== 'string' || !name.trim() || name.length > 120) throw new RequestError('Officer name is required (maximum 120 characters)');
  if (typeof identifier !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9._@+-]{2,253}$/.test(identifier.trim())) throw new RequestError('Enter a valid email or username (3-254 characters)');
  if (typeof password !== 'string' || password.length < 8 || Buffer.byteLength(password, 'utf8') > 72) throw new RequestError('Password must be at least 8 characters and no more than 72 UTF-8 bytes');
  if (password !== (confirmPassword ?? confirm_password)) throw new RequestError('Passwords do not match');
  const email = identifier.trim().toLowerCase();
  if (database.getUser(email)) throw new RequestError('An account with this email or username already exists', 409);
  const hash = await bcrypt.hash(password, 12);
  const user: UserRecord = { id: `usr-${randomUUID()}`, email, name: name.trim(), role: 'OFFICER', department: 'SIMRAS Officer Desk', created_at: new Date().toISOString() };
  try { database.runtime.addAccount(user, hash); }
  catch (error) {
    if (database.getUser(email)) throw new RequestError('An account with this email or username already exists', 409);
    throw error;
  }
  return { user, token: generateToken(user, database) };
}
