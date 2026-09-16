# SIMRAS Source-Backed L2/L3 Digital Twins — Design

Date: 2026-09-16
Branch: `feature/source-backed-l2-l3-twins-20260916`
Base: `simras-source-20260912-124514`

## 1. Goal

Upgrade SIMRAS from mostly L0/L1 approximate 3D representations to a source-first digital-twin system where the best-supported assets appear first and where geometry, dimensions, environment, ML outputs, and reports are all traceable to real evidence.

The system must never label a visual approximation as survey-exact or government-verified geometry.

## 2. Current problem

The current water fallback renderer intentionally generates L1 asset-specific approximate geometry from deterministic seeds. Those proportions are visual only. The source branch also contains several source-backed topology profiles (Prakasam Barrage, Polavaram, Srisailam, Somasila, Sir Arthur Cotton Barrage), plus airport/temple evidence pipelines, but the fidelity labels stop short of L2/L3 because detailed plan geometry/survey/CAD is not consistently available.

The new design removes seed-generated dimensions from the authoritative path whenever verified engineering topology exists.

## 3. Fidelity contract

### L3 — survey / source geometry

Use only when the repository has an actual survey-grade or authoritative geometry asset, such as CAD/BIM/IFC, point cloud, official 3D mesh, photogrammetric mesh with controlled scale, or equivalent source geometry with known coordinate/scale metadata.

Requirements:
- source geometry file or reproducible source-geometry import
- real-world scale verified
- coordinate/orientation metadata where applicable
- source/provenance recorded
- no procedural substitution presented as L3

### L2 — source-matched engineering twin

Use when exact source geometry is unavailable but authoritative component topology and dimensions are sufficient to reconstruct the major engineering form.

Requirements:
- official/authoritative length/height/width or runway/gate/span dimensions
- component counts where structural repetition is material
- identity and coordinates verified
- renderer uses evidence values directly
- any unsourced detail is clearly visual/contextual and excluded from measured dimensions

### L1 — verified-dimension parametric twin

Use when identity and some engineering measurements are verified but topology is incomplete. Geometry may be parametric, but every displayed measurement must come from evidence.

### L0 — context / approximate

Use when there is insufficient engineering evidence. Approximate geometry may be shown for context but must not be presented as a real structural replica.

## 4. Source hierarchy

Use sources in this order for structural facts:

1. Official project/CAD/BIM/survey/as-built documents
2. Government engineering/project authority pages and drawings
3. AAI eAIP aerodrome charts for airports
4. CWC / India-WRIS / KRMB / AP Water Resources records for water infrastructure
5. APSAC OGC layers for statewide location/environment context
6. Survey of India / Bhuvan terrain and map context when reuse/access permits
7. TTD / AP Endowments / ASI / IGNCA documentation for temples
8. OSM for footprint/context where an authoritative geometry source is unavailable
9. public photographs only for visual matching, never for unsupported measurement claims

Every sourced field records source URL/document, authority level, observation/publication date if available, and verification status.

## 5. First-priority L2 candidates

Priority is based on available source-backed topology, not category prestige.

### P0 — reconstruct immediately

- `AP_DAM_00002` — Polavaram Irrigation Project
  - PPA: ECRF/gated-spillway system
  - ECRF/main dam length 2454 m
  - max height 50 m
  - spillway length 1118.40 m
  - 48 radial gates, 16 m x 20 m
  - power house 960 MW (12 x 80 MW)

- `AP_DAM_00001` — Prakasam Barrage
  - KRMB / AP-government evidence
  - length 1232.92 m
  - 70 regulator gates, 12.19 m x 3.66 m
  - 6 left + 8 right scouring sluices, 5.18 m x 3.66 m
  - source-backed regulator/scour/FRL levels

- `AP_BAR_WRIS_B00131` — Sir Arthur Cotton Barrage
  - existing verified four-arm topology
  - total length 3592.67 m
  - four arm lengths/counts
  - 175 gates

- `AP_DAM_NWDP_AP01VH0059` — Srisailam Project
  - existing verified dam/gate topology and dimensions

- `AP_AIR_VOBZ` — Vijayawada Airport
  - AAI eAIP aerodrome chart and runway geometry
  - RWY 08/26, 3360 m x 45 m
  - chart depicts runway, aprons, terminal, ATC, RESA, boundary and service features

- `AP_AIR_VOTP` — Tirupati Airport
  - AAI eAIP aerodrome chart and runway geometry
  - RWY 08/26, approximately 2285/2286 m x 45 m depending source revision
  - threshold coordinates and aerodrome layout available

### P1 — promote after source validation

- Somasila Reservoir
- other airports with current AAI eAIP engineering records
- named bridges where official span/engineering topology is sufficient
- temples where TTD/AP Endowments/ASI/IGNCA plus verified footprint/dimensions are sufficient

No temple or bridge is promoted to L2 merely because photographs exist.

## 6. Data model

Introduce a normalized, source-controlled twin evidence manifest for high-fidelity profiles.

Each profile contains:

```json
{
  "asset_code": "AP_DAM_00001",
  "asset_type": "BARRAGE",
  "fidelity": "L2",
  "geometry_mode": "SOURCE_MATCHED_ENGINEERING",
  "identity_status": "VERIFIED",
  "real_world_scale_verified": true,
  "orientation": {},
  "structure": {},
  "environment": {},
  "sources": [],
  "unsupported_visual_details": []
}
```

Measured values are always separate from viewer normalization. Viewer scale may normalize the scene for camera framing, but dimension annotations display source values rather than normalized Three.js units.

## 7. Rendering architecture

Add source-backed builders separate from approximate fallback builders.

### Water infrastructure

- Polavaram: ECRF segments + gated concrete spillway + 48 radial gates + power-house context
- Prakasam: regulator bay array + distinct left/right scour sections + roadway/hoist level cues + river plane
- Sir Arthur Cotton: four-arm barrage topology with arm-specific lengths/counts
- Srisailam: gravity-dam profile + 12 crest gates + verified major dimensions

The renderer must never create a random gate count or random structural length for an L2 asset.

### Airports

Build airport geometry from AAI runway endpoints/heading/dimensions. Render runway, strip, displaced threshold/RESA when sourced, apron polygons/blocks and major terminal/ATC context only where the chart supports them. Unsourced building heights remain visual and are not shown as measurements.

### Bridges

Use subtype-specific builders only when span count/main span/pier or deck geometry has evidence. If topology is incomplete, stay L1.

### Temples

Use verified footprint, complex area, gopuram/tower dimensions and source-linked architectural layout where available. Decorative detailing inferred from photographs is visual only and does not increase fidelity.

## 8. Real-world environment

Use geospatial context independently from engineering geometry:

- APSAC OGC layers: airports, reservoirs, major rivers, roads, ASI sites, weather/water-level stations where useful
- OSM: surrounding roads/buildings/waterways where source licensing permits
- Bhuvan/SOI: terrain/elevation context where accessible and reusable

The twin's engineering geometry remains authoritative even if environment tiles fail to load. Environment failure must degrade gracefully rather than replace the twin.

## 9. Priority sorting

Add an evidence-based fidelity score and sort selected infrastructure lists by:

1. L3
2. L2
3. L1
4. L0

Within the same fidelity level, sort by evidence completeness, then asset name.

Do not use health/risk score to define digital-twin fidelity.

The UI displays a badge such as:
- `L3 SURVEY / SOURCE GEOMETRY`
- `L2 SOURCE-MATCHED ENGINEERING TWIN`
- `L1 VERIFIED-DIMENSION PARAMETRIC TWIN`
- `L0 CONTEXT MODEL`

## 10. ML and report integrity

Digital-twin fidelity must not silently upgrade ML validity.

Reports will continue to show:
- official asset facts and engineering dimensions
- current observations where available and fresh enough
- ML output only when its category/evidence gate allows it
- model/version/training scope
- prediction confidence and timestamp
- source/provenance
- explicit `WITHHELD` reason otherwise

No synthetic value is promoted to official data because the 3D twin became more realistic.

## 11. External data ingestion

Do not fetch government websites directly from the browser at render time. Instead:

- add backend/source scripts that fetch or normalize public official records
- cache normalized evidence in repository-controlled manifests or database tables
- record source URL and retrieval/publication date
- make source updates idempotent
- fail closed: if parsing changes or source access fails, retain the last verified profile and mark freshness rather than inventing replacement values

## 12. Tests and acceptance gates

Implementation is test-driven.

Required automated checks:

- L2 profiles cannot contain seed-generated engineering measurements
- an L2 asset must have at least one authoritative source and verified scale
- Polavaram builder renders exactly 48 sourced gates
- Prakasam builder renders exactly 70 regulator gates and 14 sourced scour sluices
- airport builder uses sourced runway length/width/heading
- dimension labels use evidence values, not Three.js normalized extents
- fidelity sorting places L3/L2 before L1/L0
- unsupported values render `Not available`/withheld, never a generated number
- reports retain ML evidence gates
- TypeScript build passes
- backend tests pass for evidence/fidelity serializers and report integrity

## 13. Files expected to change

Likely files/modules:

- `frontend/src/features/digital-twin/RealityTwinAssetViewer.tsx`
- `frontend/src/features/digital-twin/verifiedWaterTopologyTwin.ts`
- new `frontend/src/features/digital-twin/sourceBackedTwinRegistry.ts`
- new source-backed water/airport builders
- asset-list sorting component/service
- backend evidence/source ingestion scripts
- backend API serializer for fidelity/provenance if needed
- report source/evidence display code if the current response omits new fields
- tests for registry, builders, sorting and evidence gates

Existing L1 fallback builders remain only for assets without sufficient evidence.

## 14. Non-goals

- Do not claim photorealistic survey accuracy without source geometry.
- Do not download/rehost copyrighted photos or commercial meshes without reuse rights.
- Do not fabricate dimensions from imagery.
- Do not apply bridge models to dams, airports, or temples.
- Do not convert L2 visual context into an ML ground-truth claim.

## 15. Success criteria

The implementation is successful when:

1. P0 assets render with source-backed major structural topology and dimensions.
2. No P0 asset uses deterministic random engineering dimensions.
3. high-fidelity assets are ranked first in the infrastructure selector.
4. source/fidelity provenance is visible to the user.
5. missing evidence is explicit.
6. ML/report truthfulness is preserved.
7. builds/tests pass before merge.
