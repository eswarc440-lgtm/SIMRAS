SIMRAS OPEN PUBLIC 3D FAST TRACK
================================

NO GOOGLE CLOUD / NO API KEY / NO BILLING

Public layers:
1. OpenFreeMap + OpenStreetMap vector tiles
2. MapLibre GL JS 3D fill extrusion from OSM building heights/levels
3. Public Terrarium terrain tiles
4. OpenAerialMap / HOT imagery where available
5. SIMRAS registry asset coordinates
6. Major road network from OpenStreetMap/OpenMapTiles

Reality rules:
- OSM building footprint/height/levels = source-backed public data, not survey geometry.
- Missing OSM height does NOT become a verified engineering height.
- Dam/bridge/airport/temple dimensions continue to come from authoritative owner/government/survey sources.
- Photogrammetry/verified GLB can replace L1 geometry later without changing the viewer architecture.

Viewer:
http://127.0.0.1:8099/open_public_3d.html
