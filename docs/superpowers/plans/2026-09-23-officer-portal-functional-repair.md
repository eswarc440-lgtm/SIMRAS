# SIMRAS Officer Portal Functional Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair GIS, Digital Twin, search, AI, notifications, profile, settings, and officer navigation without replacing existing SIMRAS systems.

**Architecture:** Keep the React/Vite UI and existing API gateway. Add shared asset/location utilities and a single selected-asset URL context; extend existing API/database modules for structured search, grounded AI, workflow notifications, profile, and preferences.

**Tech Stack:** React 19, TypeScript, Vite, Express, Leaflet, Three.js, Vitest, Gemini backend SDK.

**Spec:** `docs/superpowers/specs/2026-09-23-officer-portal-functional-repair-design.md`

## Global Constraints

- Never fabricate coordinates, engineering values, telemetry, inspections, maintenance, scores, RUL, or live-source claims.
- Preserve existing asset, report, ML, authentication, API, and twin implementations.
- Use `Location not available` or approved unavailable labels for missing evidence.
- Keep Gemini credentials and officer-only data on authenticated backend routes.
- Follow the supplied phase order.

## Review Focus

- Missing/malformed coordinates must retain list records but never create markers or crash GIS (Task 1 test).
- Unknown URL asset codes must safely fall back to a real registry item without fabricated defaults (Task 2 test).
- Search must not expose officer records without authentication (Task 4 API test).
- AI follow-ups must retain current-session asset context and refuse missing evidence (Task 5 tests).
- Notification/profile/settings mutations must persist across reload and update client state immediately (Tasks 6-8 tests).

---

### Task 1: GIS Coordinate Safety

**Files:**
- Create: `src/lib/coordinates.ts`
- Create: `src/lib/coordinates.test.ts`
- Modify: `src/types/twin.ts`
- Modify: `src/components/GISMap.tsx`
- Modify: `src/components/GISCommandView.tsx`
- Modify: `package.json`

**Interfaces:**
- Produces: `normalizeCoordinates(asset): { geoJson: [number, number]; leaflet: [number, number] } | null`.
- Consumes: `AssetSummary.geometry`, optional latitude/longitude fields.

```ts
expect(normalizeCoordinates({ geometry: { type: "Point", coordinates: [80.6, 16.5] } })).toEqual({
  geoJson: [80.6, 16.5], leaflet: [16.5, 80.6],
});
expect(normalizeCoordinates({ geometry: undefined })).toBeNull();
expect(normalizeCoordinates({ latitude: 0, longitude: 0 })).toBeNull();
```

- [ ] Add Vitest and a `test` script, then write tests for valid GeoJSON, latitude/longitude fallback, NaN, absent geometry, reversed/out-of-range values, and no `0,0` fallback.
- [ ] Run `npm test -- src/lib/coordinates.test.ts`; expect failures because the normalizer is absent.
- [ ] Implement finite/range validation and update `AssetSummary.geometry` to be optional/nullable without adding fake coordinates.
- [ ] Use the normalizer in marker rendering and map focus; show `Location not available` in the list/detail panel.
- [ ] Run the focused test and `npx tsc --noEmit`.
- [ ] Commit: `git add package.json package-lock.json src/lib/coordinates.ts src/lib/coordinates.test.ts src/types/twin.ts src/components/GISMap.tsx src/components/GISCommandView.tsx && git commit -m "fix: make GIS coordinates fault tolerant"`.

### Task 2: Selected Asset URL Context and GIS Completion

**Files:**
- Create: `src/hooks/useSelectedAsset.ts`
- Create: `src/hooks/useSelectedAsset.test.ts`
- Modify: `src/App.tsx`
- Modify: `src/components/GISCommandView.tsx`
- Modify: `src/components/InspectionsManager.tsx`
- Modify: `src/components/MaintenancePlanner.tsx`

**Interfaces:**
- Produces: `useSelectedAsset(assets)` returning `{ selectedAssetCode, selectedAsset, selectAsset, buildAssetUrl }`.
- Consumes: real `AssetSummary[]` and `?asset=` URL parameter.

```ts
export function resolveSelectedAssetCode(assets: AssetSummary[], requested: string | null) {
  return assets.some((asset) => asset.asset_code === requested) ? requested : assets[0]?.asset_code ?? null;
}
```

- [ ] Write tests for URL initialization, refresh persistence, unknown codes, URL updates, and cross-view selection.
- [ ] Run the focused test; expect missing-hook failures.
- [ ] Implement the hook with `URLSearchParams` and `history.replaceState`; remove the fabricated `activeAsset` object from `App.tsx`.
- [ ] Connect GIS category/search/risk filters and route actions to Twin, Reports, Inspections, Maintenance, and AI through `selectedAssetCode`.
- [ ] Run tests and TypeScript.
- [ ] Commit: `git add src/hooks/useSelectedAsset* src/App.tsx src/components/GISCommandView.tsx src/components/InspectionsManager.tsx src/components/MaintenancePlanner.tsx && git commit -m "feat: persist selected infrastructure across workflows"`.

### Task 3: Full-Page Evidence-Backed Digital Twin

**Files:**
- Create: `src/components/twin/TwinAssessmentPanel.tsx`
- Create: `src/components/twin/TwinEvidenceTables.tsx`
- Create: `src/components/twin/twinViewModel.ts`
- Create: `src/components/twin/twinViewModel.test.ts`
- Modify: `src/components/DigitalTwinPage.tsx`
- Modify: `src/features/digital-twin/RealityTwinAssetViewer.tsx`

**Interfaces:**
- Produces: `buildTwinViewModel(asset, twin, assessment, inspections, maintenance)` with nullable evidence-backed table rows.
- Consumes: existing twin viewer and `/api/v1/assets/:code/*`, inspections, and maintenance data.

```ts
expect(buildTwinViewModel(asset, twinWithoutDimensions, assessment, [], []).dimensions).toEqual([]);
expect(buildTwinViewModel(asset, twinWithoutTelemetry, assessment, [], []).telemetryState).toBe("DATA NOT AVAILABLE");
```

- [ ] Write view-model tests proving missing values render unavailable labels and never default to `587.5 m`, `32 m`, `1995`, or synthetic live telemetry.
- [ ] Run the focused test; expect failure.
- [ ] Build the responsive 70/30 first viewport with assessment cards and preserved viewer resolution order.
- [ ] Add the two-column light tables for dimensions, telemetry, inspections, and maintenance with compact `View All` actions.
- [ ] Run tests, TypeScript, and `npm run build`.
- [ ] Commit: `git add src/components/DigitalTwinPage.tsx src/components/twin src/features/digital-twin/RealityTwinAssetViewer.tsx && git commit -m "feat: rebuild digital twin workspace"`.

### Task 4: Structured Global Search

**Files:**
- Create: `src/components/common/GlobalSearch.tsx`
- Create: `src/components/common/searchModel.ts`
- Create: `src/components/common/searchModel.test.ts`
- Modify: `src/components/common/OfficerHeader.tsx`
- Modify: `src/App.tsx`
- Modify: `server/db.ts`
- Modify: `server.ts`

**Interfaces:**
- Endpoint: `GET /api/v1/search?q=<text>` returns `{ groups: { assets, inspections, maintenance, reports } }`.
- Result: `{ type, id, title, subtitle, asset_code?, action_url }`.

```ts
type SearchResult = {
  type: "asset" | "inspection" | "maintenance" | "report";
  id: string; title: string; subtitle: string; asset_code?: string; action_url: string;
};
expect(groupSearchResults(results).assets[0].type).toBe("asset");
```

- [ ] Write tests for minimum length, grouped result mapping, keyboard index movement, empty results, and restricted-result filtering.
- [ ] Run the focused tests; expect missing search-model failures.
- [ ] Add one database search method and one authenticated endpoint using normalized case-insensitive matching.
- [ ] Implement debounced grouped dropdown, loading/error/empty states, Arrow Up/Down, Enter, and Escape; connect navigation in `App.tsx`.
- [ ] Run tests, TypeScript, and build.
- [ ] Commit: `git add src/components/common/GlobalSearch.tsx src/components/common/searchModel* src/components/common/OfficerHeader.tsx src/App.tsx server/db.ts server.ts && git commit -m "feat: add structured officer search"`.

### Task 5: Grounded AI Advisor With Session Memory

**Files:**
- Create: `server/aiContext.ts`
- Create: `server/aiContext.test.ts`
- Modify: `server/ai.ts`
- Modify: `server.ts`
- Modify: `src/components/AiAssistantDrawer.tsx`

**Interfaces:**
- Request: `{ prompt: string; selected_asset_code?: string; history: Array<{ role: "user" | "assistant"; content: string }> }`.
- Response: `{ answer, key_evidence, data_sources, limitations, suggested_next_action, asset_code }`.

```ts
const context = buildAiContext({ selectedAssetCode: "AP_DAM_00001", prompt: "What was its latest inspection?", history });
expect(context.asset?.asset_code).toBe("AP_DAM_00001");
expect(context.missingEvidence).not.toContain("inspection_history");
```

- [ ] Write tests for asset retrieval, inspection/maintenance/environment context, missing evidence, follow-up pronouns, and history truncation.
- [ ] Run tests; expect missing context-builder failures.
- [ ] Extract deterministic context retrieval; replace canned keyword templates with evidence summaries only when Gemini is unavailable.
- [ ] Update backend instruction to forbid invented values and client drawer to send selected asset plus session history.
- [ ] Execute the 15-prompt matrix and save results under `artifacts/ai-advisor-verification.json`.
- [ ] Commit: `git add server/ai* server.ts src/components/AiAssistantDrawer.tsx artifacts/ai-advisor-verification.json && git commit -m "feat: ground AI advisor in SIMRAS evidence"`.

### Task 6: Real Workflow Notifications

**Files:**
- Create: `src/components/notificationModel.ts`
- Create: `src/components/notificationModel.test.ts`
- Modify: `server/db.ts`
- Modify: `server.ts`
- Modify: `src/components/NotificationModal.tsx`
- Modify: `src/App.tsx`
- Modify: `src/components/common/OfficerSidebar.tsx`

**Interfaces:**
- Notification fields: `id, type, title, message, asset_code, entity_id, created_at, read_at, priority, action_url`.
- Filters: `unread | all | risk | inspections | maintenance | assets | reviews`.

```ts
const next = markNotificationRead(notifications, "NOTIF-001", "2026-09-23T08:00:00Z");
expect(next.find((item) => item.id === "NOTIF-001")?.read_at).toBeTruthy();
expect(unreadCount(next)).toBe(unreadCount(notifications) - 1);
```

- [ ] Write tests for workflow-event creation, filters, unread/read-all transitions, and action routing.
- [ ] Remove static badge fallbacks and any cyclic/random generation; emit notifications from existing inspection, maintenance, asset, review, and risk mutations.
- [ ] Add authenticated polling every 45 seconds only while logged in plus focus refresh and optimistic unread updates.
- [ ] Run tests, TypeScript, and build.
- [ ] Commit: `git add server/db.ts server.ts src/components/NotificationModal.tsx src/components/notificationModel* src/App.tsx src/components/common/OfficerSidebar.tsx && git commit -m "feat: connect notifications to workflow events"`.

### Task 7: Officer Navigation and Profile

**Files:**
- Create: `src/components/ProfilePage.tsx`
- Create: `src/components/profileValidation.ts`
- Create: `src/components/profileValidation.test.ts`
- Modify: `src/components/common/OfficerSidebar.tsx`
- Modify: `src/components/common/OfficerHeader.tsx`
- Modify: `src/App.tsx`
- Modify: `server/db.ts`
- Modify: `server.ts`

**Interfaces:**
- Endpoints: `GET/PATCH /api/v1/profile`, `POST/DELETE /api/v1/profile/photo`.
- Editable fields: `name, phone, email` and permission-approved department/district; immutable fields remain server-enforced.

```ts
expect(validateProfilePatch({ role: "ADMIN" })).toEqual({ role: "Role cannot be changed" });
expect(validateProfilePhoto({ type: "image/svg+xml", size: 100 })).toEqual("Use JPEG, PNG, or WebP");
```

- [ ] Write validation tests for allowed image MIME types, maximum size, immutable fields, email, and phone.
- [ ] Remove Audit Logs from the normal Officer menu and remove hardcoded sidebar counts.
- [ ] Add protected profile methods/endpoints and safe file upload handling; implement edit/save/cancel/reset UI.
- [ ] Connect header dropdown `My Profile`, `Settings`, and `Logout`.
- [ ] Run tests, TypeScript, and build.
- [ ] Commit: `git add src/components/ProfilePage.tsx src/components/profileValidation* src/components/common/OfficerSidebar.tsx src/components/common/OfficerHeader.tsx src/App.tsx server/db.ts server.ts && git commit -m "feat: add functional officer profile"`.

### Task 8: Persistent Settings

**Files:**
- Create: `src/components/SettingsPage.tsx`
- Create: `src/components/settingsModel.ts`
- Create: `src/components/settingsModel.test.ts`
- Modify: `src/App.tsx`
- Modify: `server/db.ts`
- Modify: `server.ts`

**Interfaces:**
- Endpoints: `GET/PATCH /api/v1/preferences`.
- Produces typed preference groups for General, Notifications, GIS, Twin, Reports, AI, and Accessibility.

```ts
const saved = mergePreferences(defaultPreferences, { gis: { rememberLastPosition: true } });
expect(saved.gis.rememberLastPosition).toBe(true);
expect(saved.twin.renderingQuality).toBe("auto");
```

- [ ] Write tests for defaults, validation, merge semantics, user separation, and reload serialization.
- [ ] Add per-user preference storage and authenticated routes.
- [ ] Replace the settings placeholder with controlled sections; wire preferences into GIS, Twin, Reports, AI, and accessibility behavior.
- [ ] Run tests, TypeScript, and build.
- [ ] Commit: `git add src/components/SettingsPage.tsx src/components/settingsModel* src/App.tsx server/db.ts server.ts && git commit -m "feat: persist officer preferences"`.

### Task 9: Responsive Consistency and Existing Type Errors

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/components/GISMap.tsx`
- Modify: `src/components/common/OfficerHeader.tsx`
- Modify: `src/styles.css`

**Interfaces:** Existing component props only; no new API.

- [ ] Fix the existing `AssetSummary` fallback type error by removing fabricated fallback data and fix the impossible `CRITICAL` comparison by aligning `RiskLevel` with actual backend values.
- [ ] Add responsive search/modal behavior and verify header, sidebar, viewer, tables, profile, and settings at mobile/tablet/desktop widths.
- [ ] Run `npx tsc --noEmit`, `npm test`, and `npm run build`; all must exit zero.
- [ ] Commit: `git add src/App.tsx src/components/GISMap.tsx src/components/common/OfficerHeader.tsx src/styles.css src/types/twin.ts && git commit -m "fix: align officer UI types and responsiveness"`.

### Task 10: End-to-End Verification and Run

**Files:**
- Create: `docs/verification/officer-portal-functional-repair.md`

**Interfaces:** Uses running app at `http://localhost:3000` and existing API routes.

- [ ] Run the full root test suite, `npx tsc --noEmit`, production build, and relevant backend tests; record exact counts and failures.
- [ ] Start the built server and verify `/health`, assets, search, AI, notifications, profile, and preferences endpoints.
- [ ] Manually test every route and requirement from the supplied final checklist, including malformed GIS coordinates and 15 AI prompts.
- [ ] Record PASS/FAIL with evidence; do not convert untested items to PASS.
- [ ] Commit: `git add docs/verification/officer-portal-functional-repair.md && git commit -m "test: verify officer portal repair"`.
