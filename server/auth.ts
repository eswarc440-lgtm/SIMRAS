import jwt from "jsonwebtoken";
import { db, type UserRecord } from "./db";

const JWT_SECRET = process.env.JWT_SECRET || "simras-secure-jwt-secret-key-2026";

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
    return jwt.verify(token, JWT_SECRET);
  } catch {
    return null;
  }
}

export function authenticateUser(email: string, password: string): { user: UserRecord; token: string } | null {
  const user = db.getUser(email);
  if (!user) return null;

  // Standard passwords for pre-seeded enterprise accounts
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
