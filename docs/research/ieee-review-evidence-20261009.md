# SIMRAS IEEE reviewer evidence crosswalk — repository inspection

Repository: https://github.com/eswarc440-lgtm/SIMRAS  
Inspected base commit: `7fe32243190376292601c6381ca73585e4ea9fae` (`main` when inspected).  
Review branch: `research/ieee-review-evidence-20261009`.  
Scope: evidence review only. No model retraining, model replacement, or production source-code modifications. These are *repository manifest assertions*, not a reproduced experiment.

## Comment 8 — audited commit
The exact inspected revision is `7fe32243190376292601c6381ca73585e4ea9fae`. This proves which source revision was reviewed, **not** the commit that originally produced the historical evaluation. Never substitute it for the original experiment's training commit.

## Comments 13, 14, 16, 17 — model manifest source
`ML/bridge_nbi/manifest.json` identifies:
- `model_name=simras_nbi_bridge_deterioration`; `version=nbi_transfer_20260831_203056`; `stage=RESEARCH_TRANSFER`; `model_validated=false`; features `nbi_bridge_state_v1`.
- U.S. FHWA NBI 2020–2024 manifest claims 371,883 rows / 76,902 unique bridges; training 260,701 rows / 53,925 bridges; calibration 55,182 / 11,411; test 56,000 / 11,566.
- Health MAE 0.13382287823065234; RMSE 0.3603350229952035; persistence MAE 0.08607142857142858. This original manifest's health model is **worse** than its persistence baseline.
- Risk ROC-AUC 0.9717783043236863; Brier 0.025872697795722623; F1 0.875520242149073; ECE 0.004081167381469027.
- Event-conditioned RUL MAE 0.3009084865942832 years and nominal 80% interval observed coverage 0.9621094615555064.
- The manifest records SHA-256 digests under `artifact_checksums`; these must be recomputed against actual artifact bytes to confirm integrity.
- Stage and local-validation fields prohibit presenting these U.S. NBI metrics as Andhra Pradesh validation results.

The user's separate local recovery audit reported **449,999 rows / 78,116 bridges** with split counts **315,477 / 66,770 / 67,752**, different health and RUL metrics. That recovery folder was **not present in the inspected GitHub main tree**, and those results must **not** be merged with the original manifest's sample, model or evaluation identity without corresponding artifact-level provenance.

## Comment 21 — identity and meaning of 175
`data/official/evidence_manifests/AP_BAR_WRIS_B00131_SIR_ARTHUR_COTTON_BARRAGE_EVIDENCE_MANIFEST.json` identifies the asset as **Sir Arthur Cotton Barrage (Dowleswaram Barrage)**.

- `gate_count.value=175`, `unit=count`: **70 + 43 + 23 + 39 = 175 vents/gates across the four arms**.
- Four-arm total length `total_length_m.value=3592.67` m, explained as **1437.92 + 884.45 + 469.66 + 800.64 = 3592.67 m**.
- The manifest attributes gate count and arm dimensions to an ICID technical-specifications table in the 2012 paper *160 years of Irrigation and Drainage: The Saga of GDS & KDS*, source link: https://www.icid.org/pd3_pap_Rama_Raju_.pdf .
- The original source PDF still needs independent checking before claiming externally verified measurement.
- **Quality warning:** `height_m` states `source_organization=CWC` but lists a Wikipedia URL as `source_url`; do not use this field as evidence of directly verified CWC provenance.

IEEE manuscript replacement text (pending external source verification): “The Sir Arthur Cotton (Dowleswaram) Barrage engineering manifest records **175 gate/vent openings across four arms** (70, 43, 23, and 39), not 175 separate barrage assets. It reports a combined four-arm length of 3,592.67 m. These values originate from the project's source-linked engineering evidence manifest and require checking against the cited ICID technical report before being described as independently verified.”

## Comment 9 / 26 — software source
Repository: `https://github.com/eswarc440-lgtm/SIMRAS`. To cite a fixed implementation state, reference commit `7fe32243190376292601c6381ca73585e4ea9fae` and its GitHub permalink, rather than assigning an arbitrary numeric reference identifier. Re-number all in-text references consistently after adding the entry. This link is not an immutable third-party archive.

## Remaining verification work
- **7, 12, 19, 23**: inspect implementation and run actual integration/rejection/render/export tests; do not mark passed from file presence.
- **10, 18**: retrieve dated registry and compatibility report as separate artifacts; do not conflate populations.
- **11**: provide operational confidence calculations and verify caps in active runtime; illustrative sensitivity analysis must be labeled.
- **14–17**: reconcile *recovery audit* metrics with the original 2026-08-31 manifest and the underlying files before changing paper tables.
- **15**: validate units/codes against original FHWA codebook; don't guess unknown rating scales.
- **22**: report AI advisor prompt constraints as controls, not proof of hallucination absence.
- **24**: audit secret storage, JWT authorization, consent, retention and provider data disclosures before claiming deployed security.
- **1–6, 20, 25, 26**: edit and proofread the full six-page IEEE DOCX and reviewer PDF, which were provided in chat but were not present in the inspected GitHub main tree.

**Review outcome:** Documentation of real repo provenance and a specific barrage ambiguity is improved; no experimental metric, runtime test, or complete 26/26 resolution is asserted.
