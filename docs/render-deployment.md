# SIMRAS gateway deployment

The root React application and Express gateway deploy together. Gemini is invoked
only by the gateway. The optional FastAPI service supplies PostgreSQL evidence;
it does not run a second Gemini implementation.

## Runtime configuration

Use Node 24 (the root Dockerfile already selects it). For a native Node service,
set the build command to `npm ci && npm run build` and start command to `npm start`.
For a Docker service, use the root Dockerfile. Set the health-check path to `/health`.
The gateway listens on Render's `PORT` and serves the built frontend.

Set these variables in the service's environment, never in frontend build variables:

| Variable | Value |
| --- | --- |
| `NODE_ENV` | `production` |
| `JWT_SECRET` | A strong random secret, kept stable across restarts |
| `SIMRAS_ACCOUNT_PASSWORD_HASHES` | JSON object mapping enabled account emails to bcrypt hashes |
| `GEMINI_API_KEY` | The server's Gemini API key |
| `GEMINI_MODEL` | Optional; defaults to `gemini-2.5-flash` |
| `SIMRAS_DATA_DIR` | Persistent disk mount path for standalone registration storage |
| `SIMRAS_BACKEND_URL` | Optional FastAPI base URL; leave empty for standalone operation |
| `SIMRAS_BACKEND_ADMIN_API_KEY` | Required when using FastAPI; must match its `ADMIN_API_KEY` |

Production startup refuses missing signing/account configuration and refuses
standalone storage without `SIMRAS_DATA_DIR`. Demo passwords work only in development.
Account hashes enable the existing server-owned accounts (`officer@simras.gov.in`,
`reviewer@simras.gov.in`, `admin@simras.gov.in`, and `public@simras.gov.in`). Adding a
hash for an arbitrary email does not create a new identity or role. Omit accounts
that should remain disabled. Generate hashes locally with bcrypt; keep passwords,
hash configuration and API keys out of source control and support logs.

## Standalone persistence

Attach a persistent disk at `/var/data`, set `SIMRAS_DATA_DIR=/var/data`, and leave
`SIMRAS_BACKEND_URL` empty. The gateway creates `registrations.sqlite3` there.
Submissions, review decisions and reviewer notification events are transactional
and survive process restarts. Use one instance for this SQLite deployment.

Render preserves only files beneath the disk mount path. Persistent disks require
a paid service, prevent horizontal scaling of that service, and introduce a short
interruption during deploys. See [Render persistent disks](https://render.com/docs/disks).
Setting an environment variable alone does not provision a disk. Do not mount a
blank disk over the checked-in `data` directory, which contains the source registry.

This change persists asset registration and review data. Existing profile edits,
preferences, general notifications and other legacy in-memory workflows do not
gain restart persistence from this store.

## Optional PostgreSQL deployment

Run the existing FastAPI service with its PostgreSQL/PostGIS database and migrations.
Set the gateway's backend URL and matching server-to-server admin key. Registry,
registration and review writes use FastAPI. Twin, assessment, asset GIS and report
reads use that same backend; upstream failures are returned rather than replaced
with local demonstration records. Gemini receives retrieved database evidence.

Keep FastAPI's admin key private. Browsers authenticate to the gateway with their
session token; the gateway derives submission/review identities from server accounts.
Pending and rejected registrations are excluded from the public asset registry.
Approval verifies identity and does not itself generate health, risk or RUL scores.
The existing backend must be exercised against a real PostgreSQL instance before
claiming this configuration has passed an end-to-end deployment check.

## Verification and release

Run locally before release:

```text
npm test
npm run lint
npm run build
npm run test:http
cd backend
python -m pytest -q
```

`test:http` launches the built production gateway with random test credentials and
a temporary database, verifies the role matrix and restart persistence, then cleans
up its own process and temporary storage. It disables Gemini by default and checks
the evidence-preserving fallback. It does not modify the deployed registry.

With explicit approval to send the sample evidence to Google Gemini, run
`node scripts/verify-registration.mjs --live-ai`. This uses the configured key to
check real Andhra Dam and Prakasam Barrage answers through a local production gateway.

After deploying a reviewed commit using [Render's deployment workflow](https://render.com/docs/deploy-node-express-app):

1. Verify `/health` and `/api/v1/ai/health`. `READY` means a key is configured; it is
   not proof that Google accepted a request.
2. Sign in with enabled officer credentials and ask about Andhra Dam and Prakasam
   Barrage. Verify `ai_generated: true` and the resolved asset code. An evidence
   fallback is useful but does not prove live Gemini works.
3. Submit an agreed test asset, confirm `PENDING_REVIEW`, and verify that anonymous
   asset/GIS/twin/report reads do not publish it.
4. Review using a different reviewer/admin identity. Self-review must fail and
   unassessed scores must remain null/`WITHHELD` after approval.
5. Restart the service and verify the registration and decision remain. Inspect
   the actual configured storage, not only a successful submission response.

Do not claim production verification solely from passing local tests.
