# Paper 1 reproducibility bundle

This repository now includes `reproduce_paper1.py`, a zero-cost local runner for the verified Paper 1 evidence layer.

## Run it

From the repository root:

```text
python reproduce_paper1.py
```

It writes `reproduction_report.html`. Open that file in a browser before the defense. The report includes:

- validation reporting tables;
- held-out cohort reporting tables;
- the confidence/error audit;
- selective-reporting policy comparisons;
- resistance-locus coverage evidence;
- frozen-test safety gates and limitations;
- exact SHA-256 hashes for every input artifact used.

For a validation-only run:

```text
python reproduce_paper1.py --verify-only
```

## Important scientific boundary

The current repository contains the saved final-analysis evidence tables and model artifacts, but it does not contain a complete runnable reconstruction of the original feature-extraction and training pipeline. Therefore this bundle reproduces the reported evidence layer from saved CSV/JSON artifacts and re-derives the report, rather than falsely claiming a fresh end-to-end retraining run.

The runner refuses to proceed if the saved readiness record indicates that frozen test outcomes were read, test artifacts were used, or thresholds were modified. It does not evaluate the frozen test split.
