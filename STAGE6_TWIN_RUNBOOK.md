# Stage 6A — Source-backed showcase twins

This stage ranks asset-specific twins ahead of generic L0 illustrations and
adds district, asset-type, and fidelity filters to the Digital Twin page.

## Showcase promotion

After deploying the source changes, run:

```powershell
docker compose exec backend python -m scripts.promote_showcase_twins
```

This command is idempotent. It promotes:

- Vijayawada Airport (`AP_AIR_VOBZ`)
- Tirupati Airport (`AP_AIR_VOTP`)
- Sri Venkateswara Swamy Temple, Tirumala (`AP_TEMPLE_TTD_0001`) when the
  statewide OSM temple layer is available

Load the temple layer first when necessary:

```powershell
docker compose --profile etl run --rm etl python -m simras_etl.osm_statewide --layers temple
```

## Evidence

- Airport runway and strip dimensions: Airports Authority of India eAIP.
- Tirumala complex area and main-entrance height: Tirumala Tirupati
  Devasthanams temple history page.
- Tirumala representative location: source-reported OSM landmark record.

## Fidelity boundary

The new airport and temple views are L1 dimension-derived parametric
representations. They are asset-specific and source-backed, but they are not
survey-grade meshes, BIM models, photogrammetry, or engineering-certified
as-built geometry. L2/L3 promotion requires measured footprints, drawings,
LiDAR, drone photogrammetry, or BIM evidence.

## AI boundary

The registered deterioration ML model remains bridge-only. Airport and temple
twins expose geometry and provenance but do not receive bridge health, risk,
or remaining-life inference.
