import type {RequestHandler} from 'express';

// Keep public views on the same authority as registration. Backend failures must
// never silently substitute the standalone demonstration registry.
export function backendReads(baseUrl: () => string | undefined, adminKey: () => string | undefined): RequestHandler {
  return async (req,res,next) => {
    const base = baseUrl()?.replace(/\/$/, '');
    if (!base || req.method !== 'GET') { next(); return; }
    const route = req.path.replace(/^\/api\/v1/, '');
    const direct = /^\/assets\/[^/]+\/(twin|assessment|risk-prediction|bridge-profile|inspections|maintenance)$/.test(route);
    const map = ['/gis/assets','/gis/assets/bbox','/map/features','/map-features'].includes(route);
    const reportMatch = route.match(/^\/assets\/([^/]+)\/reports\/(real|decision-support|export\/(json|csv))$/)
      ?? route.match(/^\/reports\/assets\/([^/]+)\/assessment$/);
    const detailMatch = route.match(/^\/(gis\/assets|infrastructure|digital-twin\/assets|predictions)\/([^/]+)$/);
    if (!direct && !map && !reportMatch && !detailMatch) { next(); return; }
    const api = base.endsWith('/api/v1') ? base : base+'/api/v1';
    const read = async (suffix:string, body?:object) => {
      const response = await fetch(api+suffix,{signal:AbortSignal.timeout(30000),
        ...(body ? {method:'POST',headers:{'Content-Type':'application/json','X-Admin-API-Key':adminKey() ?? ''},body:JSON.stringify(body)} : {})});
      const data = await response.json();
      if (!response.ok) throw Object.assign(new Error('Database read failed'),{status:response.status});
      return data;
    };
    try {
      if (direct) { res.json(await read(route)); return; }
      if (map) {
        const type = req.query.asset_type ?? req.query.type ?? req.query.feature_type;
        const data = await read('/assets/geojson'+(typeof type === 'string' ? '?asset_type='+encodeURIComponent(type) : ''));
        let features = data.features.map((feature:any) => ({...feature,properties:{...feature.properties,
          asset_id:feature.properties.asset_code,type:feature.properties.asset_type,feature_type:feature.properties.asset_type}}));
        if (typeof req.query.district === 'string') features = features.filter((f:any) => f.properties.district?.toLowerCase() === String(req.query.district).toLowerCase());
        if (typeof req.query.search === 'string') features = features.filter((f:any) => `${f.properties.name} ${f.properties.asset_code}`.toLowerCase().includes(String(req.query.search).toLowerCase()));
        if (typeof req.query.bbox === 'string') {
          const bounds = req.query.bbox.split(',').map(Number);
          if (bounds.length !== 4 || !bounds.every(Number.isFinite) || bounds[0] >= bounds[2] || bounds[1] >= bounds[3]) {
            res.status(422).json({error:'bbox must use min_lon,min_lat,max_lon,max_lat'}); return;
          }
          features = features.filter((f:any) => {
            const [lon,lat] = f.geometry?.coordinates ?? [];
            return lon >= bounds[0] && lon <= bounds[2] && lat >= bounds[1] && lat <= bounds[3];
          });
        }
        res.json({...data,features,total:features.length}); return;
      }
      if (reportMatch) {
        const code = reportMatch[1];
        const context = await read(`/ai/assets/${code}/context`,{prompt:'Summarize the selected asset evidence for its report.'});
        const assessments = context.assessments ?? {};
        const assessment = {status:Object.values(assessments).some((a:any) => a.value != null) ? 'EVIDENCE_AVAILABLE' : 'WITHHELD',
          health_score:assessments.health?.value ?? null,risk_score:assessments.risk?.value ?? null,
          risk_level:assessments.risk?.class ?? null,rul_years:assessments.rul?.value ?? null,
          provenance:assessments,governance:context.provenance};
        const report = {asset_profile:context.focus_asset,assessment,
          metadata:{generated_at:new Date().toISOString(),system:'SIMRAS research decision support'},
          engineering_dimensions:{metrics:context.digital_twin?.dimensions ?? {},authority:context.digital_twin?.model_source},
          environmental_conditions:null,multi_variable_prediction:null,environmental_time_series:[],seven_day_forecast:[],infra_health_care_assist:null,
          inspection_history:context.inspections ?? [],maintenance_history:context.maintenance ?? [],
          provenance:{source_references:context.source_references ?? []},limitations:context.missing_evidence ?? []};
        if (reportMatch[3] === 'csv') {
          const escape = (v:unknown) => '"'+String(v ?? '').replace(/"/g,'""')+'"';
          res.type('text/csv').send(['asset_code,name,health_score,risk_score,rul_years,status',
            [context.focus_asset.asset_code,context.focus_asset.name,assessment.health_score,assessment.risk_score,assessment.rul_years,assessment.status].map(escape).join(',')].join('\n'));
        } else res.json(report);
        return;
      }
      if (detailMatch) {
        const [,kind,code] = detailMatch;
        if (['summary','high-risk','stats','available'].includes(code)) { next(); return; }
        if (kind === 'digital-twin/assets') { res.json(await read(`/assets/${code}/twin`)); return; }
        const asset = await read(`/assets/${code}`);
        if (kind === 'gis/assets') {
          res.json({type:'Feature',id:asset.asset_code,geometry:asset.geometry,properties:{...asset,asset_id:asset.asset_code,type:asset.asset_type}});
        } else if (kind === 'predictions') {
          res.json({asset_id:asset.asset_code,asset_name:asset.name,health_score:asset.health_score ?? null,
            risk_score:asset.risk_score ?? null,remaining_useful_life_years:asset.remaining_useful_life ?? null});
        } else res.json({...asset,id:asset.asset_code,type:asset.asset_type});
      }
    } catch (error:any) {
      res.status(Number.isInteger(error.status) ? error.status : 502).json({error:error.status === 404 ? 'Asset not found' : 'Configured database backend is unavailable'});
    }
  };
}
