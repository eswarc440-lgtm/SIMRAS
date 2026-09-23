# SIMRAS Officer Portal Functional Repair Design

## Objective

Repair the existing SIMRAS application in the supplied priority order without replacing its current asset registry, APIs, authentication, reports, GIS, ML data, or digital-twin viewers. Officer workflows must use backend records, survive incomplete data, persist the active asset, and use the existing light government visual language.

## Constraints

- Reuse the current React/Vite UI, Express API gateway, FastAPI services, data stores, and twin implementations.
- Never fabricate coordinates, telemetry, engineering values, scores, inspection findings, maintenance records, or live-source claims.
- Missing evidence is displayed as `NOT AVAILABLE`, `NOT VERIFIED`, `WITHHELD`, or `Location not available`, as appropriate.
- Preserve role boundaries; officer-only search data and actions remain authenticated.
- Keep the Three.js/WebGL canvas dark where useful, but use the light government theme everywhere else.

## 1. GIS Command and Shared Asset Context

Create a single coordinate normalizer that accepts GeoJSON geometry or latitude/longitude fields, validates finite WGS84 ranges, and returns both GeoJSON `[longitude, latitude]` and Leaflet `[latitude, longitude]` forms. Invalid coordinates return `null`; GIS skips only the marker while lists retain the asset with `Location not available`.

GIS search and category/risk filters operate on the loaded registry and support DAM, BARRAGE, BRIDGE, AIRPORT, and TEMPLE. Popups show identity, category, district, scores, provenance, and actions. Map focus never dereferences geometry directly.

The application owns one `selectedAssetCode`. It initializes from the `asset` URL parameter, resolves against the registry, and updates URLs for Digital Twin and Reports. GIS, Reports, Inspections, Maintenance, and AI consume the same resolved selection.

## 2. Digital Twin Layout and Evidence

Preserve `RealityTwinAssetViewer` and its asset-specific models. The first viewport becomes a responsive 70/30 layout: full-height viewer on the left and compact assessment/metrics panel on the right. Mobile collapses this vertically without hiding the viewer.

Below the viewer, use a two-column light dashboard containing compact Engineering Dimensions, Telemetry, Inspections, and Maintenance tables. Values come from existing asset, twin, inspection, maintenance, and assessment endpoints. Remove hardcoded dimensional and live telemetry fallbacks. Empty tables show honest unavailable states. Environmental charts and evidence remain optional lower sections when records exist.

Viewer resolution order remains: existing realistic twin, GLB/GLTF, asset-specific parametric twin, labelled proxy. The viewer must never be blank.

## 3. Global Search

Add one authenticated structured search endpoint covering permitted assets, inspections, work orders, and reports. Results include entity type, primary label, secondary label, asset code, entity ID, and action URL.

The header search activates at two characters, debounces requests, groups results, and provides loading, empty, and error states. Arrow keys, Enter, and Escape are supported. Selecting a result updates the active asset and opens the matching existing view.

## 4. AI Engineering Advisor

Keep model calls backend-only. The advisor request sends the question, selected asset code, and current-session conversation history. The orchestration layer retrieves relevant SIMRAS asset, assessment, evidence, inspection, maintenance, environmental, report, and documentation context before calling Gemini.

Remove canned question/answer routing as the primary behavior. The system instruction forbids invented evidence and directs the response to include answer, evidence, source, limitations, and next action when useful. Missing evidence produces the required unavailable message. Session memory is temporary and does not modify official records.

## 5. Notifications

Use stored workflow events rather than timers, random values, or cyclic demo arrays. Notification records expose ID, type, title, message, asset code, entity ID, creation/read timestamps, priority, and action URL. Read and read-all mutations update UI counts immediately.

The authenticated client loads on login/focus and polls every 45 seconds while logged in. Filters cover unread, all, risk, inspections, maintenance, assets, and reviews. Action links select the asset and navigate to the related record.

## 6. Navigation and Officer Access

Remove Audit Logs from the normal Officer sidebar while leaving backend audit functionality intact. The sidebar order follows the supplied target. Administrative audit access remains role-gated if already supported.

## 7. Profile

Create an authenticated profile view backed by the existing user record. Officers may edit allowed contact fields but not officer ID, role, or approval authority. Photo upload accepts JPEG, PNG, or WebP with size validation and safe file-backed storage where supported. Save, cancel, reset, validation, confirmation, and reload persistence are required.

## 8. Settings

Create a real settings page grouped into General, Notifications, GIS, Digital Twin, Reports, AI Advisor, and Accessibility. Persist account-level preferences through the API where supported; harmless display-only preferences may use namespaced local storage. Only expose settings that affect implemented behavior.

## 9. Header and UI Consistency

The Officer header keeps its existing appearance while connecting search, AI, notifications, profile, settings, and logout. The avatar dropdown routes to Profile and Settings. Responsive layouts prevent overlap and provide compact controls. Shared colors remain `#F5F7FA`, `#FFFFFF`, `#0C4775`, `#0875BE`, and `#DDE5EC`.

## 10. Verification

Add focused tests for coordinate normalization, asset URL persistence, grouped search, AI context/memory, notification mutations, profile validation, and settings persistence. Verify TypeScript, production build, relevant backend tests, and the running application.

Manual browser checks cover GIS, Digital Twin, Reports, Dashboard, Inspections, Maintenance, Notifications, Profile, Settings, and AI Advisor. Fifteen materially different AI prompts cover asset, inspection, maintenance, environment, assessment, help, missing data, and follow-up context. The final report uses PASS only when the corresponding automated or manual evidence exists.

## Delivery Order

Implementation is split into independently verifiable increments matching the requested order: GIS/context, Digital Twin, search, AI, notifications, sidebar, profile, settings, header consistency, and end-to-end verification. Each increment reuses existing interfaces and lands without a cross-system rewrite.
