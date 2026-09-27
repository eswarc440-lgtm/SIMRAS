import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import bcrypt from "bcryptjs";
import {
  createHash,
  randomBytes,
  randomInt,
  randomUUID,
} from "node:crypto";
import type { UserRecord } from "./db";

export interface RegisterAccountInput {
  full_name: string;
  officer_id: string;
  email: string;
  password: string;
}

interface AccountRow {
  id: string;
  email: string;
  officer_id: string;
  full_name: string;
  role: string;
  department: string;
  password_hash: string;
  active: number;
  created_at: string;
  updated_at: string;
}

export class AccountStore {
  private database: DatabaseSync;

  constructor(file: string) {
    if (file !== ":memory:") {
      fs.mkdirSync(path.dirname(file), { recursive: true });
    }

    this.database = new DatabaseSync(file);

    this.database.exec(`
      PRAGMA journal_mode=WAL;

      CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        officer_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS password_reset_codes (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL COLLATE NOCASE,
        code_hash TEXT NOT NULL,
        token_hash TEXT,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 0,
        verified_at TEXT,
        created_at TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_password_reset_email
      ON password_reset_codes(email, created_at);
    `);
  }

  private normalizeEmail(email: string) {
    return String(email ?? "").trim().toLowerCase();
  }

  private validateEmail(email: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  private validatePassword(password: string) {
    if (typeof password !== "string" || password.length < 8 || password.length > 128) {
      throw new Error("Password must contain between 8 and 128 characters.");
    }
  }

  private rowByIdentity(identity: string): AccountRow | null {
    const value = String(identity ?? "").trim();

    if (!value) return null;

    const row = this.database
      .prepare(`
        SELECT *
        FROM accounts
        WHERE lower(email)=lower(?)
           OR lower(officer_id)=lower(?)
        LIMIT 1
      `)
      .get(value, value) as unknown as AccountRow | undefined;

    return row ?? null;
  }

  public getAccount(identity: string) {
    return this.rowByIdentity(identity);
  }

  public getUserRecord(identity: string): UserRecord | null {
    const row = this.rowByIdentity(identity);
    if (!row || !row.active) return null;

    return {
      id: row.id,
      email: row.email,
      name: row.full_name,
      role: row.role as UserRecord["role"],
      department: row.department,
      created_at: row.created_at,
    };
  }

  public ensureAccount(
    user: UserRecord,
    passwordHash: string,
    officerId = user.id,
  ) {
    const now = new Date().toISOString();

    this.database.prepare(`
      INSERT OR IGNORE INTO accounts
      (
        id,email,officer_id,full_name,role,department,
        password_hash,active,created_at,updated_at
      )
      VALUES (?,?,?,?,?,?,?,?,?,?)
    `).run(
      user.id,
      user.email.toLowerCase(),
      officerId,
      user.name,
      user.role,
      user.department,
      passwordHash,
      1,
      user.created_at || now,
      now,
    );
  }

  public registerAccount(input: RegisterAccountInput): UserRecord {
    const fullName = String(input.full_name ?? "").trim();
    const officerId = String(input.officer_id ?? "").trim();
    const email = this.normalizeEmail(input.email);
    const password = String(input.password ?? "");

    if (fullName.length < 2 || fullName.length > 100) {
      throw new Error("Full name must contain between 2 and 100 characters.");
    }

    if (officerId.length < 3 || officerId.length > 50) {
      throw new Error("Officer ID must contain between 3 and 50 characters.");
    }

    if (!/^[A-Za-z0-9._/-]+$/.test(officerId)) {
      throw new Error("Officer ID contains unsupported characters.");
    }

    if (!this.validateEmail(email)) {
      throw new Error("Enter a valid email address.");
    }

    this.validatePassword(password);

    const duplicate = this.database.prepare(`
      SELECT id
      FROM accounts
      WHERE lower(email)=lower(?)
         OR lower(officer_id)=lower(?)
      LIMIT 1
    `).get(email, officerId) as unknown as { id: string } | undefined;

    if (duplicate) {
      throw new Error("An account already exists with this email or Officer ID.");
    }

    const now = new Date().toISOString();
    const id = `usr-${randomUUID()}`;
    const passwordHash = bcrypt.hashSync(password, 12);

    this.database.prepare(`
      INSERT INTO accounts
      (
        id,email,officer_id,full_name,role,department,
        password_hash,active,created_at,updated_at
      )
      VALUES (?,?,?,?,?,?,?,?,?,?)
    `).run(
      id,
      email,
      officerId,
      fullName,
      "OFFICER",
      "SIMRAS Infrastructure Operations",
      passwordHash,
      1,
      now,
      now,
    );

    return {
      id,
      email,
      name: fullName,
      role: "OFFICER",
      department: "SIMRAS Infrastructure Operations",
      created_at: now,
    };
  }

  public verifyPassword(identity: string, password: string) {
    const row = this.rowByIdentity(identity);

    if (!row || !row.active || typeof password !== "string") {
      return false;
    }

    return bcrypt.compareSync(password, row.password_hash);
  }

  public createPasswordReset(emailInput: string):
    | { email: string; code: string; expiresAt: string }
    | null {
    const email = this.normalizeEmail(emailInput);
    const account = this.rowByIdentity(email);

    if (!account || account.email.toLowerCase() !== email || !account.active) {
      return null;
    }

    const cutoff = new Date(Date.now() - 15 * 60 * 1000).toISOString();

    const recent = this.database.prepare(`
      SELECT COUNT(*) AS count
      FROM password_reset_codes
      WHERE lower(email)=lower(?)
        AND created_at >= ?
    `).get(email, cutoff) as unknown as { count: number };

    if (Number(recent?.count ?? 0) >= 5) {
      throw new Error("Too many password reset requests. Try again later.");
    }

    this.database.prepare(`
      UPDATE password_reset_codes
      SET used=1
      WHERE lower(email)=lower(?)
        AND used=0
    `).run(email);

    const code = String(randomInt(100000, 1000000));
    const codeHash = bcrypt.hashSync(code, 10);
    const createdAt = new Date().toISOString();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

    this.database.prepare(`
      INSERT INTO password_reset_codes
      (
        id,email,code_hash,expires_at,used,
        attempts,created_at
      )
      VALUES (?,?,?,?,?,?,?)
    `).run(
      randomUUID(),
      email,
      codeHash,
      expiresAt,
      0,
      0,
      createdAt,
    );

    return { email, code, expiresAt };
  }

  public verifyResetCode(emailInput: string, codeInput: string): string | null {
    const email = this.normalizeEmail(emailInput);
    const code = String(codeInput ?? "").trim();

    const row = this.database.prepare(`
      SELECT *
      FROM password_reset_codes
      WHERE lower(email)=lower(?)
        AND used=0
      ORDER BY created_at DESC
      LIMIT 1
    `).get(email) as unknown as any;

    if (!row) return null;
    if (Number(row.attempts ?? 0) >= 5) return null;
    if (new Date(String(row.expires_at)).getTime() < Date.now()) return null;

    this.database.prepare(`
      UPDATE password_reset_codes
      SET attempts=attempts+1
      WHERE id=?
    `).run(row.id);

    if (!bcrypt.compareSync(code, String(row.code_hash))) {
      return null;
    }

    const token = randomBytes(32).toString("hex");
    const tokenHash = createHash("sha256").update(token).digest("hex");

    this.database.prepare(`
      UPDATE password_reset_codes
      SET token_hash=?,
          verified_at=?
      WHERE id=?
    `).run(
      tokenHash,
      new Date().toISOString(),
      row.id,
    );

    return token;
  }

  public resetPassword(
    emailInput: string,
    resetToken: string,
    newPassword: string,
  ): boolean {
    const email = this.normalizeEmail(emailInput);
    this.validatePassword(newPassword);

    const row = this.database.prepare(`
      SELECT *
      FROM password_reset_codes
      WHERE lower(email)=lower(?)
        AND used=0
        AND token_hash IS NOT NULL
      ORDER BY created_at DESC
      LIMIT 1
    `).get(email) as unknown as any;

    if (!row) return false;
    if (!row.verified_at) return false;
    if (new Date(String(row.expires_at)).getTime() < Date.now()) return false;

    const suppliedHash = createHash("sha256")
      .update(String(resetToken ?? ""))
      .digest("hex");

    if (suppliedHash !== String(row.token_hash)) {
      return false;
    }

    const passwordHash = bcrypt.hashSync(newPassword, 12);
    const now = new Date().toISOString();

    this.database.exec("BEGIN IMMEDIATE");

    try {
      this.database.prepare(`
        UPDATE accounts
        SET password_hash=?,
            updated_at=?
        WHERE lower(email)=lower(?)
      `).run(passwordHash, now, email);

      this.database.prepare(`
        UPDATE password_reset_codes
        SET used=1
        WHERE id=?
      `).run(row.id);

      this.database.exec("COMMIT");
      return true;
    } catch (error) {
      this.database.exec("ROLLBACK");
      throw error;
    }
  }

  public close() {
    this.database.close();
  }
}

const authDatabasePath = process.env.VITEST
  ? ":memory:"
  : path.resolve(
      process.env.SIMRAS_DATA_DIR || "data/runtime",
      "auth.sqlite3",
    );

export const accountStore = new AccountStore(authDatabasePath);