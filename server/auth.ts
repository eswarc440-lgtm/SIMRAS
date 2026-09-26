import jwt from "jsonwebtoken";
import { randomBytes } from 'node:crypto';
import bcrypt from 'bcryptjs';
import { db, type UserRecord } from "./db";

if (process.env.NODE_ENV === 'production' && !process.env.JWT_SECRET) throw new Error('JWT_SECRET is required in production to preserve authenticated sessions');
if (process.env.NODE_ENV === 'production' && !process.env.SIMRAS_ACCOUNT_PASSWORD_HASHES) throw new Error('SIMRAS_ACCOUNT_PASSWORD_HASHES is required in production; demo passwords are disabled');
const JWT_SECRET = process.env.JWT_SECRET || randomBytes(48).toString('hex');

export function normalizeRole(value: unknown): UserRecord['role'] {
  const role = String(value ?? '').trim().toUpperCase();
  return ['PUBLIC','OFFICER','REVIEWER','ADMIN'].includes(role) ? role as UserRecord['role'] : 'PUBLIC';
}

export function resolveAuthenticatedUser(claims: any): UserRecord | null {
  if (!claims || typeof claims.email !== 'string') return null;
  const user = db.getUser(claims.email);
  if (!user || user.id !== claims.id) return null;
  return {...user,role:normalizeRole(user.role)};
}

export function generateToken(user: UserRecord): string {
  return jwt.sign(
    {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      department: user.department,
    },
    JWT_SECRET,
    { expiresIn: "24h" }
  );
}

export function verifyToken(token: string): any {
  try {
    return resolveAuthenticatedUser(jwt.verify(token, JWT_SECRET, {algorithms:['HS256']}));
  } catch {
    return null;
  }
}

export function authenticateUser(email: string, password: string): { user: UserRecord; token: string } | null {
  if (typeof email !== 'string' || typeof password !== 'string') return null;
  const user = db.getUser(email);
  if (!user) return null;

  const configured = process.env.SIMRAS_ACCOUNT_PASSWORD_HASHES;
  if (configured || process.env.NODE_ENV === 'production') {
    try {
      const hashes = JSON.parse(configured || '{}');
      const hash = hashes[email.toLowerCase()];
      if (typeof hash !== 'string' || !bcrypt.compareSync(password, hash)) return null;
      return {user, token:generateToken(user)};
    } catch { return null; }
  }

  // Local development only. Production enables accounts through password hashes.
  const validPasswords: Record<string, string> = {
    "admin@simras.gov.in": "Admin@123",
    "officer@simras.gov.in": "Officer@123",
    "reviewer@simras.gov.in": "Reviewer@123",
    "public@simras.gov.in": "Public@123",
  };

  const expected = validPasswords[email.toLowerCase()];
  if (!expected || expected !== password) {
    return null;
  }

  const token = generateToken(user);
  return { user, token };
}
