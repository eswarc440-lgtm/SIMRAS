import jwt from "jsonwebtoken";
import { randomBytes } from "node:crypto";
import bcrypt from "bcryptjs";
import { db, type UserRecord } from "./db";
import { accountStore } from "./accountStore";

if (process.env.NODE_ENV === "production" && !process.env.JWT_SECRET) {
  throw new Error(
    "JWT_SECRET is required in production to preserve authenticated sessions",
  );
}

const JWT_SECRET =
  process.env.JWT_SECRET ||
  randomBytes(48).toString("hex");

export function normalizeRole(value: unknown): UserRecord["role"] {
  const role = String(value ?? "").trim().toUpperCase();

  return ["PUBLIC", "OFFICER", "REVIEWER", "ADMIN"].includes(role)
    ? (role as UserRecord["role"])
    : "PUBLIC";
}

function configuredPasswordHashes(): Record<string, string> {
  try {
    const parsed = JSON.parse(
      process.env.SIMRAS_ACCOUNT_PASSWORD_HASHES || "{}",
    );

    if (!parsed || typeof parsed !== "object") return {};

    return Object.fromEntries(
      Object.entries(parsed).map(([email, hash]) => [
        email.toLowerCase(),
        String(hash),
      ]),
    );
  } catch {
    return {};
  }
}

// Preserve configured legacy government sandbox accounts without
// overwriting a password that has already been changed in the
// persistent account database.
for (const [email, hash] of Object.entries(configuredPasswordHashes())) {
  const user = db.getUser(email);

  if (user && hash) {
    accountStore.ensureAccount(user, hash, user.id);
  }
}

export function resolveAuthenticatedUser(claims: any): UserRecord | null {
  if (!claims || typeof claims.email !== "string") return null;

  let user =
    db.getUser(claims.email) ||
    accountStore.getUserRecord(claims.email) ||
    undefined;

  if (!user || user.id !== claims.id) return null;

  user = {
    ...user,
    role: normalizeRole(user.role),
  };

  db.upsertUser(user);
  return user;
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
    {
      expiresIn: "24h",
      algorithm: "HS256",
    },
  );
}

export function verifyToken(token: string): any {
  try {
    return resolveAuthenticatedUser(
      jwt.verify(token, JWT_SECRET, {
        algorithms: ["HS256"],
      }),
    );
  } catch {
    return null;
  }
}

export function registerUser(input: {
  full_name: string;
  officer_id: string;
  email: string;
  password: string;
}) {
  const user = accountStore.registerAccount(input);
  db.upsertUser(user);

  return {
    user,
    token: generateToken(user),
  };
}

export function authenticateUser(
  identity: string,
  password: string,
): { user: UserRecord; token: string } | null {
  if (
    typeof identity !== "string" ||
    typeof password !== "string"
  ) {
    return null;
  }

  const persistentAccount =
    accountStore.getAccount(identity);

  if (persistentAccount) {
    if (!accountStore.verifyPassword(identity, password)) {
      return null;
    }

    const user = accountStore.getUserRecord(identity);
    if (!user) return null;

    db.upsertUser(user);

    return {
      user,
      token: generateToken(user),
    };
  }

  // Backward compatibility for existing configured accounts.
  const legacyUser = db.getUser(identity);

  if (legacyUser) {
    const hashes = configuredPasswordHashes();
    const hash = hashes[legacyUser.email.toLowerCase()];

    if (hash) {
      if (!bcrypt.compareSync(password, hash)) return null;

      accountStore.ensureAccount(
        legacyUser,
        hash,
        legacyUser.id,
      );

      return {
        user: legacyUser,
        token: generateToken(legacyUser),
      };
    }
  }

  // Development-only sandbox credentials.
  if (process.env.NODE_ENV !== "production") {
    const validPasswords: Record<string, string> = {
      "admin@simras.gov.in": "Admin@123",
      "officer@simras.gov.in": "Officer@123",
      "reviewer@simras.gov.in": "Reviewer@123",
      "public@simras.gov.in": "Public@123",
    };

    const user = db.getUser(identity);
    const expected =
      validPasswords[String(identity).toLowerCase()];

    if (
      user &&
      expected &&
      expected === password
    ) {
      return {
        user,
        token: generateToken(user),
      };
    }
  }

  return null;
}