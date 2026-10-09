# Reviewer resolution status — 26 comments (2026-10-09)

The six-page IEEE revision and the full reviewer-response matrix have been prepared outside the GitHub checkout from the uploaded manuscript and reviewer PDF. Existing model files and production routes were not changed.

| Comments | Assessment |
|---|---|
| 1,2,3,4,6,9,25 | Writing/citation issue addressed in revision |
| 5,8,10,11,13,14,15,17,18,20,21,23,24,26 | Partial; some required evidence remains |
| 16 | Evaluation reported; model *does not beat persistence* |
| 7,12,19 | Runtime/integration verification not completed |
| 22 | Scope caveat added; hallucination evaluation not done |

Important findings:

- Source model manifest: `ML/bridge_nbi/manifest.json`, version `nbi_transfer_20260831_203056`. Original artifact MAE=0.13382287823065234; persistence=0.08607142857142858. Existing hash declarations are not a recomputed hash check.
- Local recovered audit values from the user's agent (449,999 rows, 78,116 bridges) refer to an *unreconciled separate evaluation*. Do not merge its health/RUL metrics into original manuscript Table II.
- Source manifest for Sir Arthur Cotton Barrage identifies **175 vents across four arms**, not 175 assets; `gate_count` refers to 70+43+23+39. The original ICID technical source remains to be checked directly.
- Inspected code revision `7fe32243190376292601c6381ca73585e4ea9fae` is not proved to be the historical training commit.
- Runtime tests for governance rejection, assessment export consistency and 3D rendering have not been executed in this review session.

The revised 6-page manuscript and all-26 reviewer responses exist as conversation deliverables. They are not included as binaries in this branch. To reach 26 verified closures, run and attach test evidence, verify scientific sources, and link model artifacts to their exact panels.