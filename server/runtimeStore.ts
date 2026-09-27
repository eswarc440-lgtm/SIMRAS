import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { randomBytes } from 'node:crypto';
import type { AssetRecord, UserRecord } from './db';

// Runtime writes are isolated from canonical assets and government/ML datasets.
export class RuntimeStore {
  private connection: DatabaseSync;
  constructor(file = process.env.SIMRAS_RUNTIME_DB || path.resolve('data/runtime/registrations.sqlite3')) {
    if (file !== ':memory:') fs.mkdirSync(path.dirname(file), { recursive: true });
    this.connection = new DatabaseSync(file);
    this.connection.exec(`PRAGMA busy_timeout=5000;
      PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS registrations(asset_code TEXT PRIMARY KEY, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS officer_accounts(identifier TEXT PRIMARY KEY, password_hash TEXT NOT NULL, profile TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS runtime_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);`);
  }
  registrations(): AssetRecord[] {
    return this.connection.prepare('SELECT payload FROM registrations').all().map(row => JSON.parse(String(row.payload)));
  }
  addAsset(asset: AssetRecord) {
    this.connection.prepare('INSERT INTO registrations(asset_code,payload) VALUES (?,?)').run(asset.asset_code, JSON.stringify(asset));
  }
  account(identifier: string): { user: UserRecord; hash: string } | undefined {
    const row = this.connection.prepare('SELECT profile,password_hash FROM officer_accounts WHERE identifier=?').get(identifier);
    return row ? { user: JSON.parse(String(row.profile)), hash: String(row.password_hash) } : undefined;
  }
  addAccount(user: UserRecord, hash: string) {
    this.connection.prepare('INSERT INTO officer_accounts(identifier,password_hash,profile) VALUES (?,?,?)').run(user.email, hash, JSON.stringify(user));
  }
  updateProfile(user: UserRecord) {
    this.connection.prepare('UPDATE officer_accounts SET profile=? WHERE identifier=?').run(JSON.stringify(user), user.email);
  }
  signingSecret(): string {
    this.connection.prepare('INSERT OR IGNORE INTO runtime_settings(key,value) VALUES (?,?)').run('jwt_secret', randomBytes(48).toString('hex'));
    return String(this.connection.prepare('SELECT value FROM runtime_settings WHERE key=?').get('jwt_secret')!.value);
  }
  close() { this.connection.close(); }
}
