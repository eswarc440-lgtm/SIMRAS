# Andhra Pradesh infrastructure coverage, evidence and digital twins

Status: proposed design for user review. No new assets have been published by this audit.

## User objective

Expand SIMRAS to cover all Andhra Pradesh dams, bridges, barrages, temples and
airports, using government portals and websites, evidence-backed digital twins,
and predictions for every asset where the evidence supports them. The user
explicitly confirmed **all Andhra Pradesh coverage**, including smaller assets.

Coverage means identifying and reconciling every record available from the
selected public inventories, tracking inaccessible inventories and unresolved
records. It cannot be represented as 100% of physical infrastructure without an
authoritative denominator. Every asset gets a prediction eligibility result;
missing evidence produces a reason and required inputs, not an invented score.

Include road, rail and pedestrian bridges. Record airports/airstrips and their
operational, proposed, under-construction or closed status separately. Temple
complexes can contain multiple structural components without counting each
gopuram or shrine as an unrelated duplicate asset. Preserve asset lifecycle dates
and historical evidence; an old inventory is not proof of present operation.

## Audit findings from this workspace

The active standalone gateway loads `data/canonical_assets_194.json`:

| Type | Current entries |
| --- | ---: |
| Dam | 167 |
| Barrage | 10 |
| Bridge | 2 |
| Airport | 8 |
| Temple | 7 |
| Total | 194 |

Every row has a source URL and stored scores, but that does not establish a
field-level citation or a validated current assessment. Several URLs point only
to agency homepages. Existing synthetic inspection and telemetry initializers
must not be presented as evidence for newly ingested or reconciled real assets.

Historical reports dated September 3, 2026 provide leads, not a verified current
database state:

- `backend/reports/STEP6C2B_STATEWIDE_BRIDGE_IMPORT.json` records 23,121 OSM
  line segments, 15,120 proposed structure groups and 946 multi-segment groups
  requiring review. Neither segments nor unreviewed groups are verified physical
  bridge counts. The gateway currently exposes only two bridge baseline entries.
- `backend/reports/STEP4B_AIRPORT_ENGINEERING_REPORT.json` records eight asset
  rows for six physical airports, with two duplicated ICAO identifiers.
- `backend/reports/STEP5C_TEMPLE_ENGINEERING_REPORT.json` records evidence for
  seven temples and zero structural condition labels. Identity/history sources
  alone cannot support structural health or remaining-life predictions.
- Existing WRIS, bridge, airport and temple importers and the Three.js viewer
  provide reusable code. Several scripts assume container path `/app`.

## Proposed approach and alternatives

Recommended: extend the existing PostgreSQL/PostGIS evidence model and importers,
and publish a versioned evidence snapshot for the standalone gateway. Both modes
must consume equivalent asset IDs, field provenance and assessment eligibility.
Preserve existing officer submissions and review decisions during refreshes.

Alternatives considered: manually enlarging the current JSON would not provide
repeatable acquisition, reconciliation or source history; replacing the whole
application would discard working registration, GIS and twin functionality.

## Source acquisition

Sources located during this audit:

| Asset/source | Entry point | Audit finding |
| --- | --- | --- |
| Dams: CWC/NDSA NRLD | https://cwc.gov.in/national-register-large-dams | Official page links to NRLD 2023; its link date does not make the underlying inventory current |
| Dams/barrages: India-WRIS | https://indiawris.gov.in/ | Existing importer identifies an ArcGIS dam query endpoint; pagination and current availability need verification |
| Water projects: AP WRD/KRMB/PPA | Existing individual project references in the registry | Fetch exact project records and engineering documents, not homepage citations |
| Bridges: APRDC | https://aprdc.ap.gov.in/Documents/DISCLOSURES/ENVIRONMENT/Rajamundry.pdf | Search locates an official project report with cross-drainage inventory; browser extraction rejected its 17 MB size |
| Bridges: MoRTH/NHAI | https://morth.nic.in/node/16763 | Official Setu Bharatam entry point; public access to a full asset-level IBMS export remains unverified |
| Rail bridges: Indian Railways | https://scr.indianrailways.gov.in/ | Existing registered government source; discover bridge-specific documents |
| Airports: AAI | https://www.aai.aero/en/southern-region-airports | Regional directory found; direct fetch timed out during audit |
| Airport dimensions: AAI AIS/eAIP | Existing airport-specific eAIP references | Verify publication validity, ICAO identities, runway components and changes |
| Temples: AP Endowments | https://tms.ap.gov.in/ | Official portal found; web text extraction returned no content |
| Protected temple sites: ASI | https://asi.nic.in/admin/whatsnew/download/719 | Official national PDF includes an Andhra Pradesh section; filter temple sites from other monuments |
| Temple authorities | Existing TTD and individual devasthanam references | Identity, component dimensions and conservation records must retain exact citations |

These are acquisition entry points, not a claim that every field or complete
inventory is available. Supplementary OSM geometry may assist discovery and
matching, with its attribution and licence retained; it is not government evidence.
Do not import pre-bifurcation Andhra Pradesh lists without checking current state
boundaries and historical district mappings.

Each acquisition stores publisher, exact URL, publication/observation date where
known, retrieval time, content hash, usage terms, parser version and raw snapshot.
Downloads use bounded retries and conditional requests; pagination or partial
downloads are recorded explicitly. Blocked sources become coverage gaps. Login,
CAPTCHA or access restrictions are not bypassed. No messages to agencies are sent
without separate authorization.

## Identity and field evidence

Use stable canonical asset IDs with source identifiers and aliases. Prefer NRLD
identifiers for dams, owner bridge IDs where available, ICAO codes for airports,
and department/ASI identifiers for temples. Use name, coordinates, owner, district
and structural type as corroboration; names alone are insufficient for merging.

Retain multiple geometry segments beneath a reviewed physical bridge identity.
Keep dams, barrages, reservoir water bodies and bridge-over-barrage components
distinct when sources describe distinct structures. Airport aliases resolve to
one airport with child runway/terminal records. Preserve old IDs as redirects so
existing reports and bookmarks continue working.

Store field value, unit, source-document ID, page/table/row or web locator, source
date, extraction method and verification status. Conflicting values remain
visible for review. Unknown coordinates remain null: show the record in the
registry with a location gap, without inventing a map marker. Spatial filtering
uses a sourced AP boundary and records cross-border ownership separately.

## Digital twins

Provide an asset detail/twin page for every canonical identity. The geometry
status determines what can responsibly be rendered:

- Location/context: a sourced marker or footprint; no invented engineering scale.
- Approximate model: an explicitly labelled category model with unsourced
  proportions separated from actual measurements.
- Source-backed parametric model: asset-specific dimensions, orientation, spans,
  gates, runway geometry or temple components supported by cited records.
- Survey/reconstruction model: licensed CAD, survey or imagery-derived geometry,
  with scale, alignment, source date and validation metadata.

Generate geometry from reusable category builders and evidence records, replacing
the need to hand-code a profile for each asset. Display unknown dimensions as
unknown and expose evidence alongside measurements. Load detailed 3D models on
demand; no statewide download of all meshes on first page load.

## Predictions

The existing assessment service becomes the shared source for GIS summaries,
digital twin, reports and advisor. Each result stores target, asset/component,
input evidence IDs, feature version, model version, training scope, validation
status, prediction time, uncertainty and withholding reasons.

- Bridges: structural-condition models require relevant inspection and loading
  evidence. Transfer models retain research labels until locally validated.
- Dams/barrages: hydrologic operational forecasts stay separate from structural
  condition. Gate, foundation and material evidence cannot be replaced by rainfall.
- Airports: define runway/pavement/component predictions; do not claim an airport
  safety score from runway length or passenger volume.
- Temples: conservation/structural component assessments require suitable survey
  or inspection evidence. Age and religious significance are not condition labels.
- RUL: publish only for a defensible target and validated method with sufficient
  evidence; any permitted engineering baseline is separately labelled and never
  represented as validated ML remaining life.

Do not train on the app's seeded scores or fabricate labels, accuracy or confidence.
Evaluate with asset-grouped/time-held-out data and calibration/error metrics.
Every asset receives AVAILABLE, RESEARCH_ONLY or WITHHELD assessment status with
specific missing inputs. A visible twin does not imply prediction eligibility.

## Delivery sequence

1. Reconcile the active registry with recoverable earlier imports; inventory raw
   files, live database availability, duplicates, evidence and validation artifacts.
2. Build repeatable government-source acquisition and field evidence extraction.
   Start with the severe bridge coverage gap while acquiring the other categories.
3. Review identity matches and publish a versioned statewide registry. Add cursor
   pagination, map bounds/clustering and search that is not capped at 1,000 assets.
4. Bind category twin builders to the evidence contract and show fidelity/gaps.
5. Connect evidence-gated assessments and train/evaluate only where eligible data
   exists. Remove synthetic defaults from real asset views and exports.
6. Reconcile counts against each source inventory; publish a coverage report with
   imported, deduplicated, quarantined, unavailable and prediction-eligible counts.
7. Verify locally and against configured storage before preparing a deployment.

## Acceptance checks

- Rerunning importers is idempotent; refreshes preserve officer submissions.
- An asset detail and evidence report exist for every published canonical record.
- Published record counts reconcile with source snapshots and reviewed exclusions;
  no hard-coded 194 total or undocumented claim of complete statewide coverage.
- Bridges are counted as physical structures after reconciliation, not raw segments.
- Source citations resolve to saved evidence with the relevant field locator.
- Null geometry, stale records, conflicts and unknown measurements stay explicit.
- Every visible measured dimension has evidence; approximate model dimensions
  cannot be exported as measured engineering dimensions.
- Prediction eligibility, model validation and withholding are consistent across
  twin, API, advisor and PDF/CSV/JSON reports.
- Boundary, identifier collision, pagination, unavailable-source and duplicate
  fixtures exercise ingestion; full suite, build and storage restart checks pass.
- Coverage and unresolved public-data gaps are reported separately from software
  completion. Production publication requires deployment access and final checks.
