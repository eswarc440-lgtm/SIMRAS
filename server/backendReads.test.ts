import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import express from 'express';
import type {Server} from 'node:http';
import {once} from 'node:events';
import {backendReads} from './backendReads';

describe('configured backend read consistency', () => {
  let upstream: Server;
  let gateway: Server;
  let base: string;
  const code = 'AP_BR_REMOTE';
  const asset = {asset_code:code,name:'Remote bridge',asset_type:'bridge',district:'Krishna',
    geometry:{type:'Point',coordinates:[80.5,16.5]},health_score:null,risk_score:null};
  beforeAll(async () => {
    const database = express();
    database.use(express.json());
    database.get('/api/v1/assets/geojson', (_req,res) => res.json({type:'FeatureCollection',features:[{type:'Feature',id:code,geometry:asset.geometry,properties:asset}]}));
    database.get(`/api/v1/assets/${code}`, (_req,res) => res.json(asset));
    database.get(`/api/v1/assets/${code}/twin`, (_req,res) => res.json({asset,ai:{health_score:null,status:'WITHHELD'}}));
    database.get(`/api/v1/assets/${code}/assessment`, (_req,res) => res.json({asset_code:code,status:'WITHHELD'}));
    database.get(`/api/v1/assets/${code}/inspections`, (_req,res) => res.json([{id:17,date:'2026-09-20',type:'VISUAL',score:65,quality_flag:'UNVERIFIED'}]));
    database.post(`/api/v1/ai/assets/${code}/context`, (req,res) => {
      if (req.headers['x-admin-api-key'] !== 'test-key') return res.sendStatus(403);
      res.json({focus_asset:asset,assessments:{health:{value:null,status:'WITHHELD'},risk:{value:null,status:'WITHHELD'},rul:{value:null,status:'WITHHELD'}},
        inspections:[],maintenance:[],source_references:[],missing_evidence:['inspection_history']});
    });
    database.use((_req,res) => res.status(404).json({detail:'Asset not found'}));
    upstream = database.listen(0,'127.0.0.1'); await once(upstream,'listening');
    const app = express();
    app.use(backendReads(() => `http://127.0.0.1:${(upstream.address() as any).port}`, () => 'test-key'));
    app.use((_req,res) => res.status(418).json({error:'Unexpected local registry fallback'}));
    gateway = app.listen(0,'127.0.0.1'); await once(gateway,'listening');
    base = `http://127.0.0.1:${(gateway.address() as any).port}`;
  });
  afterAll(async () => {
    await Promise.all([gateway,upstream].filter(Boolean).map(server => new Promise<void>(resolve => server.close(() => resolve()))));
  });
  it('reads remote twin and assessment instead of falling back to local records', async () => {
    for (const route of [`/assets/${code}/twin`,`/assets/${code}/assessment`]) {
      const response = await fetch(base+'/api/v1'+route);
      expect(response.status).toBe(200);
      expect(JSON.stringify(await response.json())).toContain('WITHHELD');
    }
  });
  it('includes remote approved registrations in GIS and map results', async () => {
    for (const route of ['/gis/assets','/map/features','/map-features']) {
      const response = await fetch(base+'/api/v1'+route);
      expect(response.status).toBe(200);
      expect((await response.json()).features[0].properties.asset_code).toBe(code);
    }
  });
  it('builds reports from database evidence without invented predictions', async () => {
    const response = await fetch(`${base}/api/v1/assets/${code}/reports/real`);
    expect(response.status).toBe(200);
    const report = await response.json();
    expect(report.asset_profile.name).toBe('Remote bridge');
    expect(report.assessment.health_score).toBeNull();
    expect(report.multi_variable_prediction).toBeNull();
    expect(report.limitations).toContain('inspection_history');
  });
  it('loads the remote inspection records used by the report table', async () => {
    const response = await fetch(`${base}/api/v1/assets/${code}/inspections`);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([{id:17,date:'2026-09-20',type:'VISUAL',score:65,quality_flag:'UNVERIFIED'}]);
  });
  it('preserves database privacy failures on twin and report routes', async () => {
    for (const route of ['/assets/PRIVATE/twin','/assets/PRIVATE/reports/real']) {
      expect((await fetch(base+'/api/v1'+route)).status).toBe(404);
    }
  });
});
