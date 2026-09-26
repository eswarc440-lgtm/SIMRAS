import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';

// Standalone deployment store. On Render this path MUST be on a persistent disk.
export class RegistrationStore {
  private database: DatabaseSync;
  constructor(file: string) {
    if (file !== ':memory:') fs.mkdirSync(path.dirname(file), {recursive:true});
    this.database = new DatabaseSync(file);
    this.database.exec(`PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS registrations(asset_code TEXT PRIMARY KEY, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS registration_events(id INTEGER PRIMARY KEY, asset_code TEXT NOT NULL, payload TEXT NOT NULL);`);
  }
  list(): any[] { return this.database.prepare('SELECT payload FROM registrations ORDER BY asset_code').all().map(r => JSON.parse(String(r.payload))); }
  notifications(): any[] { return this.database.prepare('SELECT id, payload FROM registration_events ORDER BY id DESC').all().map(r => ({...JSON.parse(String(r.payload)),id:`REG-${r.id}`})); }
  markRead(id?: string) {
    for (const event of this.notifications()) {
      if (id && event.id !== id) continue;
      this.database.prepare('UPDATE registration_events SET payload=? WHERE id=?').run(JSON.stringify({...event,read:true,read_at:new Date().toISOString()}),Number(event.id.slice(4)));
    }
    return true;
  }
  create(asset: any) {
    this.database.exec('BEGIN IMMEDIATE');
    try {
      this.database.prepare('INSERT INTO registrations VALUES (?, ?)').run(asset.asset_code,JSON.stringify(asset));
      this.event(asset, 'Asset submitted for review');
      this.database.exec('COMMIT');
      return asset;
    } catch (error) { this.database.exec('ROLLBACK'); throw error; }
  }
  private event(asset: any, title: string) {
    const timestamp = new Date().toISOString();
    this.database.prepare('INSERT INTO registration_events(asset_code,payload) VALUES (?,?)').run(asset.asset_code,JSON.stringify({title,message:`${asset.name} (${asset.asset_code}): ${asset.status}`,asset_code:asset.asset_code,category:'REVIEW',severity:'INFO',read:false,timestamp,created_at:timestamp,action_url:'/reviews',recipient_roles:['REVIEWER','ADMIN']}));
  }
  review(code: string, user: {id:string;role:string}, decision: string, comments: string) {
    if (!['REVIEWER','ADMIN'].includes(user.role)) throw new Error('Reviewer or Admin authorization required');
    if (!['APPROVED','REJECTED'].includes(decision)) throw new Error('Decision must be APPROVED or REJECTED');
    if (!comments.trim()) throw new Error('Review comments are required');
    this.database.exec('BEGIN IMMEDIATE');
    try {
      const row = this.database.prepare('SELECT payload FROM registrations WHERE asset_code=?').get(code);
      if (!row) throw new Error('Registration not found');
      const asset = JSON.parse(String(row.payload));
      if (asset.created_by === user.id) throw new Error('You cannot review your own registration');
      if (asset.status !== 'PENDING_REVIEW') throw new Error('Registration is no longer pending review');
      Object.assign(asset,{status:decision === 'APPROVED' ? 'VERIFIED' : 'REJECTED',identity_status:decision === 'APPROVED' ? 'VERIFIED' : 'REJECTED',reviewed_by:user.id,reviewed_at:new Date().toISOString(),review_comments:comments});
      this.database.prepare('UPDATE registrations SET payload=? WHERE asset_code=?').run(JSON.stringify(asset),code);
      this.event(asset, 'Asset registration reviewed');
      this.database.exec('COMMIT');
      return asset;
    } catch (error) { this.database.exec('ROLLBACK'); throw error; }
  }
  close() { this.database.close(); }
}
