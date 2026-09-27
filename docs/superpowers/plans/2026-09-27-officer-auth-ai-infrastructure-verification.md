# SIMRAS verification — 2026-09-27

Implemented against checkpoint `33088c0`. Source and SQLite backups are in `safety_backup_20260927_140444/` (ignored by Git and blocked from HTTP access).

## Verified

- `npm.cmd run lint`: passed.
- `npx.cmd vitest run --exclude '**/*backup*/**'`: 51 tests passed across 13 files. Covers password hashing, confirmation validation, duplicate/concurrent registration, restart persistence, all five infrastructure categories, invalid submissions, selected-asset evidence and hydrology joins.
- `npm.cmd run build`: passed. Existing large-chunk warning remains.
- API integration: real account registration/login; duplicate rejection; safe invalid credentials; infrastructure submission and retrieval; null predictions through asset, infrastructure, prediction, twin and report APIs; GIS inclusion.
- Complete server restart: test account and infrastructure persisted and remained retrievable.
- Real Gemini responses: selected Kanaka Durga Flyover question distinguished registry scores, sparse estimates and missing current inspection evidence. Newly registered asset questions returned unavailable/pending evidence.
- Browser: Create Account, sign out, created-account sign in, four-step infrastructure submission with a review step, pending scores, correct advisor target, session restoration and a visible single AP emblem at desktop/mobile widths. Final production browser run had no JavaScript errors.
- Confidentiality: built client assets do not contain GEMINI_API_KEY or its value. Development and production requests for SQLite, WAL, `/@fs` database paths, server files and `.env` returned 404.
- Preservation: canonical JSON SHA-256 matches the pre-change backup. All 194 canonical assets remain available. The main runtime database's pre-existing registration is also available, for 195 main-server assets. Government/bridge/ML datasets were not modified.
- Independent review findings about runtime-file access, unavailable scores and hydrology joins were fixed and rechecked.

## Runtime

- Main local server refreshed at `http://localhost:3000`.
- Accounts and submitted assets persist in `data/runtime/registrations.sqlite3`; hashes remain separate from public user profiles. Existing registration tables and records are preserved.
- Uses the existing `GEMINI_API_KEY` from the server environment / `.env.local` / `.env`. Windows system CAs are trusted without disabling TLS verification. `GEMINI_MODEL` can override the existing default model.
- Runtime uses Node's SQLite support (verified with Node 24). Keep the runtime database on persistent storage when hosting this single-server app.
- Existing sandbox role presets remain available. This change does not introduce officer-identity approval or a password-reset workflow.
- Repeat isolated API verification with `scripts/verify-officer-flows.mjs`; use `--restart-check` after restarting the same test database. The verification scripts intentionally use separate test databases, not main-server accounts/assets.
