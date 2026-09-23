# SIMRAS FINAL ML VALIDATION REPORT

Run ID: `20260903_020557`

## Final verdict

**NO DEFENSIBLE MODEL — no suitable real labelled dataset was available.**

## Required interpretation

- The script does not manufacture a 97-98% score.
- Risk uses a locked asset-separated test set.
- 97% risk accuracy alone is insufficient; balanced accuracy, ROC-AUC, recall, Brier score and ECE must also pass.
- Health is regression and is evaluated with MAE, RMSE, R² and predicted-vs-actual agreement.
- Asset overlap between training and test must be zero.
- Synthetic/demo rows are removed when explicitly marked.
- Unsupported RUL is not trained or promoted.
- A transfer model is not labelled as Andhra Pradesh production accuracy.

## Promotion summary

- Production eligible: 0
- Validated transfer models: 0
- Rejected/research only: 0

## Model results

## Real-vs-predicted evidence

See:

`09_PREDICTED_VS_ACTUAL.csv`

and:

`10_ERROR_ANALYSIS.csv`

These files are the primary evidence for whether model outputs match held-out real-world labels.