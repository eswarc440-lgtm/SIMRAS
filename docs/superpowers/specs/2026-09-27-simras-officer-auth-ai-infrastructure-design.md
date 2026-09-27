# SIMRAS Officer Authentication, AI Advisor and Infrastructure Submission Design

Date: 2026-09-27

## Goal

Upgrade the existing SIMRAS application without redesigning the current website.

The changes are:

1. Remove the blue circular SIMRAS logo from the header.
2. Replace that position with the existing Andhra Pradesh Government emblem.
3. Preserve SIMRAS, OFFICER DESK, navigation, styling and current page structure.
4. Add real Create Account support for officers.
5. Store accounts persistently with hashed passwords.
6. Repair the SIMRAS AI Engineering Advisor using the existing server-side GEMINI_API_KEY.
7. Make Add Infrastructure submit and persist a real infrastructure record.
8. Preserve all existing bridge, dam, barrage, airport and temple data.

## Header

Current unwanted blue circular logo must be removed.

Required result:

[AP GOVERNMENT EMBLEM] SIMRAS [OFFICER DESK]

Do not duplicate the emblem.

Do not redesign the navbar.

Do not change existing navigation, colors or responsive structure unless required to remove the logo.

## Authentication

Create Account must be a real persistent account flow.

Required fields:

- Officer name
- Email or username
- Password
- Confirm password

Requirements:

- unique login identifier
- password must never be stored as plaintext
- bcrypt or equivalent password hashing
- registration endpoint
- login endpoint
- validation for duplicate accounts
- invalid credentials return a safe error
- password/hash must never be returned to frontend

Preferred endpoints:

POST /api/auth/register
POST /api/auth/login

Use the existing SIMRAS server/database architecture rather than introducing Firebase/Auth0.

## AI Engineering Advisor

Use the existing server-side GEMINI_API_KEY.

Never expose GEMINI_API_KEY to frontend code.

Frontend sends:

- question
- selected asset identifier

Backend loads SIMRAS context for the selected asset including available:

- asset identity
- infrastructure type
- Health score
- Risk score
- Risk level
- RUL
- prediction confidence
- engineering dimensions
- ML/evidence status
- inspections
- maintenance
- rainfall
- hydrology
- traffic where available
- government/source provenance

The advisor must distinguish:

- official measurement/evidence
- model prediction
- sparse/model estimate
- unavailable evidence

It must not invent structural inspection values.

The generic message:

"The engineering advisor is currently unavailable."

should only appear for a genuine service failure.

## Add Infrastructure

The existing Add Infrastructure page must have a working Submit / Add Infrastructure button.

Minimum required inputs:

- infrastructure name
- infrastructure type
- latitude
- longitude

Accept additional existing engineering fields from the form where available.

Backend must:

1. validate request
2. generate/use an asset identifier
3. persist infrastructure
4. return created record
5. make created asset available to normal asset/GIS retrieval

Preferred endpoint:

POST /api/v1/infrastructure

A newly created infrastructure must not receive fabricated Health/Risk/RUL values.

Prediction values remain unavailable/model-pending until the SIMRAS evidence/ML pipeline produces them.

## Infrastructure Scope

Preserve support for existing SIMRAS infrastructure categories and current project data.

No bridge datasets, government evidence, ML data or existing infrastructure records may be deleted.

## Safety

Before implementation:

- create Git checkpoint
- create backups of every modified source file
- do not use git clean -fd
- do not use git reset --hard
- do not overwrite bridge evidence datasets
- do not replace the current website with another frontend

## Verification

Implementation is successful only when:

1. frontend build passes
2. blue header logo is gone
3. AP emblem remains visible
4. Create Account creates a persistent account
5. created account can log in
6. duplicate account is rejected
7. AI Advisor answers a selected-asset question
8. Gemini key remains server-side
9. Add Infrastructure creates a persistent asset
10. created asset appears through the application's asset/infrastructure API
11. existing SIMRAS infrastructure remains available
12. existing website design remains unchanged apart from requested changes
