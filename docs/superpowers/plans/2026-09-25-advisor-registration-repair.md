# Advisor and registration repair implementation plan

**Goal:** Repair existing advisor and asset submission without rebuilding SIMRAS.

**Architecture:** Keep the Express gateway and existing React views. Gemini runs only in the gateway using `@google/genai` and server configuration. PostgreSQL supplies evidence when configured; the local registry is explicitly labelled unverified. Registrations use a transactional SQLite store on a configured persistent disk for standalone deployment, or the existing PostgreSQL backend. Roles come from authenticated server records.

**Constraints:** Never expose secrets; never fabricate assessments; officers submit PENDING_REVIEW; only reviewers/admins review and never their own submission. Preserve existing workspace edits. No production success claim without live Gemini and persisted registration checks.

## Phase 1 — Diagnose
- [x] Inspect frontend, gateway, Python backend, deployment, and live endpoints.
- [x] Identify separate AI implementations, absent health endpoint, token/cache identity mismatch, volatile registrations, and fabricated defaults.

## Phase 2 — Implement
- [x] Add regression tests for advisor health/fallback/resolution, role handling, durable submissions, review and self-approval protection.
- [x] Centralize Gemini generation, retrieval, safe diagnostics and evidence fallback.
- [x] Validate frontend sessions with auth/me and authorize mutations with server user records.
- [x] Persist registrations/review events in standalone SQLite; surface queue and notifications; withhold scores and pending public GIS visibility. PostgreSQL review metadata is persisted, but notification events still use the standalone store.
- [x] Document Render runtime variables and persistent disk configuration.

## Phase 3 — Verify
- [x] Run Node tests, TypeScript, Python tests and production build.
- [x] Exercise role matrix and restart persistence through real local HTTP endpoints.
- [ ] Check deployed health, Andhra Dam queries and Prakasam resolution.
- [ ] Deploy only a reviewable tested change using available authenticated Render access; verify real Gemini answers and database/review queue persistence.

## Review focus
Expired or tampered sessions must fail closed; unknown roles normalize to PUBLIC; ambiguous names return choices; provider errors never discard evidence; missing assessments stay null/WITHHELD. Deployment access and runtime secrets must be verified independently from local .env.

## Continuation record — 2026-09-26

Resumed the existing uncommitted workspace without relocating or discarding prior
edits. No separate advisor/registration design spec was present; this plan supplied
the scope. Work remains uncommitted for review.

Review fixes: public observations no longer expose pending registrations; approved
unassessed dams/barrages return WITHHELD forecasts; PostgreSQL twin, assessment,
GIS and report reads use the configured backend; VALIDATED_LOCAL predictions retain
ML provenance. Report scores now preserve nulls, clear stale predictions on asset
changes, and use database-backed inspection reads. Scenario calculations retain
the original assessment as their baseline.

Ruling: retain the existing working directory and unrelated edits — the user's
instruction is to continue unfinished work here; a fresh checkout would omit it.
Ruling: use HTTP fixtures to test PostgreSQL gateway routing without asserting a
real PostgreSQL deployment was exercised. Real database persistence remains a
deployment acceptance check.

Outstanding external checks: no deployed URL or authenticated Render access is
available in this session. Browser connection failed because its sandbox metadata
was unavailable. Automatic approval review rejected the live Gemini request because
sending the sample evidence requires explicit user approval; approval was requested.
No production deploy or real Gemini completion is claimed.

Final verification: `npm test` 72/72; `npm run lint` passes; `npm run build`
passes (existing large-chunk warning); Python `pytest -q` 67/67;
`npm run test:http` passes against the rebuilt gateway, including restart
persistence, authentication/role checks, public visibility, self-review denial,
WITHHELD forecasts and evidence fallback. `git diff --check` passes.
