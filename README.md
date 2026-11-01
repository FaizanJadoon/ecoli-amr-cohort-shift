# High-Confidence False-Susceptible Predictions Under Cohort Shift

### An Antibiotic-Specific Evaluation of Genomic Resistance Models in *Escherichia coli*

Research code and verified evidence for an exploratory retrospective study of high-confidence false-susceptible predictions in genomic antimicrobial resistance (AMR) models under cohort shift.

## Research objective

This study examines whether genomic AMR models can produce confidently incorrect susceptible predictions when evaluated on different bacterial cohorts.

The analysis focuses on three antibiotics:

- Ciprofloxacin
- Ceftriaxone
- Gentamicin

The central questions concern false-susceptible errors, antibiotic-specific reporting, confidence thresholds, and the trade-off between withholding predictions and reportability.

## Data sources

Research data were collected from public resources including:

- NCBI Pathogen Detection and associated phenotype records
- NCBI genomic assemblies and sequence archives
- BV-BRC bacterial genomic and antimicrobial susceptibility resources

Raw sequencing data and intermediate genomic datasets are excluded from this repository because of their size.

## Research analyses

The saved evidence includes:

1. Validation reporting comparisons
2. Exploratory held-out cohort reporting
3. High-confidence false-susceptible error auditing
4. Selective-reporting policy comparisons
5. Resistance-locus sequencing-coverage evidence
6. Evidence provenance and scientific limitations

## Reproducibility

The main reproduction script is:

    python reproduce_paper1.py

It validates saved research evidence and generates:

    reproduction_report.html

For evidence verification without retaining a report:

    python reproduce_paper1.py --verify-only

The reproduction runner uses the Python standard library.

See `REPRODUCE_PAPER1.md` for details.

### Important reproduction boundary

This repository supports reproduction of the saved evidence report from final-analysis CSV, JSON, and Markdown artifacts.

It does not contain a complete runnable reconstruction of the original genomic feature-extraction and model-training pipeline.

The reproduction runner does not evaluate the frozen test split.

## Repository structure

- `reproduce_paper1.py` — Evidence verification and report generation
- `REPRODUCE_PAPER1.md` — Reproduction instructions
- `reproduction_report.html` — Generated evidence report
- `results/final_analysis/manuscript_evidence/` — Verified research evidence
- `src/` — Available auxiliary genomic analysis scripts
- `requirements.txt` — Dependencies for auxiliary scripts

## Scientific limitations

- The study is exploratory and retrospective.
- Model scores are not necessarily calibrated probabilities.
- Explored held-out cohorts are not equivalent to an untouched final test.
- Some upstream training and feature-extraction code is unavailable.
- Sequencing-coverage evidence does not establish causal classifier failure.
- The results do not establish clinical readiness.

## Research status

The repository is intended to support transparent inspection of the available research evidence and its limitations.

It is not a clinically validated antimicrobial susceptibility prediction system.

## Author

Faizan Khan
