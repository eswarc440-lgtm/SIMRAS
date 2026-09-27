# SIMRAS implementation plan

Follow the supplied 2026-09-27 design in the existing Express/React application.

1. Preserve the current Git state, back up modified sources and the existing SQLite registration store. Never modify canonical assets or evidence datasets.
2. Add a SQLite runtime-store module using the existing registrations table. Add officer accounts with a unique normalized identifier, bcrypt hashes and public-only user projections. Keep current seeded logins working through hashed verification. Load persisted registrations without replacing canonical entries.
3. Add registration/login endpoint aliases at /api/auth and /api/v1/auth. Validate names, identifiers, confirmation and bcrypt byte limits; reject duplicates and bad credentials. Add Create Account mode within the current officer login page.
4. Normalize and validate infrastructure submissions, preserve optional engineering values, generate collision-resistant identifiers, and persist before returning success. Serve the record through existing asset, infrastructure and GIS APIs. Leave Health/Risk/RUL/confidence null and model-pending; never accept submitted predictions as authoritative.
5. Load server environment before initialization. Retrieve selected-asset context and available source artifacts on the server, distinguish estimates and unverified workflow records, and exclude generated telemetry from measurements. Return meaningful client errors and genuine Gemini service failures separately.
6. Replace the blue emblem component with the existing AP image and remove the extra officer-header image. Preserve navbar classes and page layout.
7. Verify persistence across database/server restart, duplicate and invalid requests, auth response redaction, null pending predictions through retrieval, selected-asset Gemini responses, frontend build/type checks and browser flows. Compare canonical/evidence hashes and inspect the final diff.

Review focus: concurrent duplicate registration, malformed coordinates, durable writes before success, selected-asset isolation, generated telemetry falsely presented as official evidence. Use temporary SQLite databases for automated tests and retain the existing runtime record.
