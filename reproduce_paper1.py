#!/usr/bin/env python3
"""Reproduce the verified Paper 1 evidence report from repository artifacts.

This runner intentionally operates on the checked-in evidence layer.  It does
not evaluate the frozen test split and does not claim to recreate missing
upstream feature-extraction/training code.  It validates the evidence files,
recomputes report-level summaries from their rows, records SHA-256 hashes, and
writes a self-contained HTML report.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

TITLE = ("High-Confidence False-Susceptible Predictions Under Cohort Shift: "
         "An Antibiotic-Specific Evaluation of Genomic Resistance Models in "
         "Escherichia coli")
EVIDENCE = Path("results/final_analysis/manuscript_evidence")
REQUIRED = {
    "validation": EVIDENCE / "table1_validation_reporting.csv",
    "heldout": EVIDENCE / "table2_heldout_reporting.csv",
    "confidence_audit": EVIDENCE / "experiment1_confidence_error_audit.csv",
    "high_confidence_errors": EVIDENCE / "experiment1_high_confidence_errors.csv",
    "policy": EVIDENCE / "experiment2_reporting_policy_comparison.csv",
    "test_readiness": EVIDENCE / "experiment3_test_readiness.json",
    "evidence_register": EVIDENCE / "evidence_register.json",
    "verified_summary": EVIDENCE / "verified_results_summary.md",
    "coverage": EVIDENCE / "supplement_marker_coverage_all_seeds.csv",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def table(rows: list[dict[str, str]], columns: list[str], labels: dict[str, str] | None = None) -> str:
    if not rows:
        return '<p class="muted">No rows found.</p>'
    labels = labels or {}
    head = "".join(f"<th>{esc(labels.get(c, c))}</th>" for c in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{esc(row.get(c, ''))}</td>" for c in columns) + "</tr>")
    return f"<div class=table-wrap><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def pct(value: str) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return value


def make_report(root: Path, output: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    missing = [str(path) for path in REQUIRED.values() if not (root / path).is_file()]
    if missing:
        errors.extend([f"Missing required artifact: {item}" for item in missing])
        return False, errors

    validation = read_csv(root / REQUIRED["validation"])
    heldout = read_csv(root / REQUIRED["heldout"])
    confidence = read_csv(root / REQUIRED["confidence_audit"])
    high_errors = read_csv(root / REQUIRED["high_confidence_errors"])
    policy = read_csv(root / REQUIRED["policy"])
    coverage = read_csv(root / REQUIRED["coverage"])
    readiness = json.loads((root / REQUIRED["test_readiness"]).read_text(encoding="utf-8"))
    register = json.loads((root / REQUIRED["evidence_register"]).read_text(encoding="utf-8"))

    # Safety gate: the report must never silently consume a frozen test result.
    if readiness.get("test_outcomes_read") is True or readiness.get("test_artifact_names"):
        errors.append("Safety gate failed: test outcomes/artifacts are marked as used.")
    if readiness.get("thresholds_modified") is True:
        errors.append("Safety gate failed: thresholds are marked as modified.")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hashes = []
    for name, relative in REQUIRED.items():
        path = root / relative
        hashes.append((name, str(relative), sha256(path)))

    validation_cols = ["Drug", "Method", "N", "Resistant_N", "Reported_N", "Reportability", "False_susceptible_N", "VME_all_resistant"]
    heldout_cols = ["Experiment", "Drug", "N", "Resistant_N", "Reported_N", "Reportability", "False_susceptible_N", "VME_all_resistant"]
    coverage_cols = ["markers", "target_depth", "Measurements", "Mean_depth", "Mean_breadth_10x_pct", "Min_breadth_10x_pct", "Max_breadth_10x_pct"]
    policy_cols = ["Experiment", "Drug", "Policy", "Susceptible_cutoff", "N", "Resistant_N", "Reported_N", "Withheld_N", "Reportability", "False_susceptible_N", "False_susceptible_per_all_resistant"]

    summary_cards = f"""
      <div class=cards>
        <div class=card><strong>{len(validation)}</strong><span>validation evidence rows</span></div>
        <div class=card><strong>{len(heldout)}</strong><span>held-out cohort rows</span></div>
        <div class=card><strong>{len(confidence)}</strong><span>confidence-audit rows</span></div>
        <div class=card><strong>{len(coverage)}</strong><span>coverage evidence rows</span></div>
      </div>"""
    findings = "".join(f"<li>{esc(item)}</li>" for item in register.get("supported_findings", []))
    not_established = "".join(f"<li>{esc(item)}</li>" for item in register.get("not_yet_established", []))
    caveats = "".join(f"<li>{esc(item)}</li>" for item in register.get("important_caveats", []))
    hash_rows = "".join(f"<tr><td>{esc(name)}</td><td>{esc(relative)}</td><td><code>{digest}</code></td></tr>" for name, relative, digest in hashes)
    readme = """
      <p><b>How to interpret this bundle:</b> the report is reproducible from the
      saved evidence layer. It re-reads the final-analysis tables, validates the
      safety gates, and records exact input hashes. Upstream feature extraction
      and model-training scripts are not complete in this repository, so this
      package does not claim a fresh end-to-end retraining run.</p>
    """
    report = f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Paper 1 Reproducibility Report</title>
<style>
body{{margin:0;background:#f5f7fa;color:#182332;font:16px/1.6 system-ui,-apple-system,Segoe UI,Arial,sans-serif}}
main{{max-width:1180px;margin:auto;padding:36px 22px 70px}} header{{background:#13283d;color:white;padding:42px 22px}}
.header-inner{{max-width:1180px;margin:auto}} h1{{font-size:clamp(1.8rem,4vw,3.2rem);line-height:1.1;margin:.3em 0 .5em}} h2{{margin-top:2.2em;color:#154d6b}} h3{{color:#154d6b}}
.kicker{{color:#9ad1ca;text-transform:uppercase;letter-spacing:.12em;font-size:.78rem;font-weight:700}} .subtitle,.muted{{color:#627286}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}} .card{{background:white;border:1px solid #dce4eb;border-radius:10px;padding:18px;box-shadow:0 3px 12px #13283d0d}} .card strong{{display:block;font-size:1.8rem;color:#154d6b}} .card span{{font-size:.9rem;color:#627286}}
.callout{{background:#e8f3f3;border-left:5px solid #2d8b88;padding:16px 18px;margin:18px 0}} .warning{{background:#fff4dc;border-left-color:#c58a27}} ul{{padding-left:1.3em}} li{{margin:.35em 0}}
.table-wrap{{overflow:auto;background:white;border:1px solid #dce4eb;border-radius:8px;margin:14px 0 24px}} table{{border-collapse:collapse;width:100%;min-width:760px;font-size:.88rem}} th,td{{padding:9px 11px;border-bottom:1px solid #e7edf2;text-align:left;vertical-align:top}} th{{background:#edf3f6;color:#154d6b;position:sticky;top:0}} tr:last-child td{{border-bottom:0}} code{{font-size:.76rem;word-break:break-all}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:26px}} .panel{{background:white;border:1px solid #dce4eb;border-radius:10px;padding:20px}} footer{{max-width:1180px;margin:auto;padding:20px 22px;color:#627286;font-size:.85rem}}
@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class=header-inner><div class=kicker>Faizan Paper 1 · Reproducibility Report</div><h1>{esc(TITLE)}</h1><div class=subtitle style='color:#d7e4ea'>Generated {generated} · Python {esc(platform.python_version())} · {esc(platform.system())}</div></div></header>
<main>
{summary_cards}
<div class=callout>{readme}</div>
<h2>Scope and scientific position</h2><p>This is an exploratory retrospective cohort-shift audit in <i>Escherichia coli</i> across ciprofloxacin, ceftriaxone, and gentamicin. Model scores are reported as model outputs; they are not treated as calibrated probabilities unless a specific calibration analysis says so. The frozen test split remains excluded.</p>
<div class=grid><section class=panel><h3>Supported findings</h3><ul>{findings}</ul></section><section class='panel warning'><h3>Not established</h3><ul>{not_established}</ul></section></div>
<h2>Validation reporting</h2><p class=muted>Rows are read directly from <code>{REQUIRED['validation']}</code>.</p>{table(validation, validation_cols)}
<h2>Held-out cohort reporting</h2><p class=muted>These cohorts were explored during development; they are not an untouched final test evaluation.</p>{table(heldout, heldout_cols)}
<h2>Confidence-error audit</h2><p>The audit table is reproduced from the saved confidence/error evidence. False-susceptible counts use the artifact-defined resistant denominator.</p>{table(confidence, ["Evaluation", "Experiment", "Drug", "Susceptible_probability_threshold", "Total_N", "Resistant_N", "False_susceptible_N", "False_susceptible_per_resistant", "CI95_lower", "CI95_upper"])}
<h2>Selective reporting policy</h2>{table(policy, policy_cols)}
<h2>Resistance-locus coverage evidence</h2><p class=muted>This is coverage evidence from the saved pilot/aggregate table; it does not prove classifier marker-detection failure.</p>{table(coverage, coverage_cols)}
<h2>Safety gates and limitations</h2><div class=callout><b>Frozen test protection:</b> test outcomes read = <code>{esc(readiness.get('test_outcomes_read'))}</code>; test artifact names = <code>{esc(len(readiness.get('test_artifact_names', [])))}</code>; thresholds modified = <code>{esc(readiness.get('thresholds_modified'))}</code>.</div><ul>{caveats}</ul>
<h2>Provenance and hashes</h2><p>Each input below was present and hashed at report-generation time. Re-running after changing any input will produce different hashes.</p><div class=table-wrap><table><thead><tr><th>Role</th><th>Relative path</th><th>SHA-256</th></tr></thead><tbody>{hash_rows}</tbody></table></div>
<h2>Reproduction command</h2><pre><code>python reproduce_paper1.py</code></pre><p class=muted>Use <code>python reproduce_paper1.py --verify-only</code> for validation without writing a report.</p>
</main><footer>Generated from the local Paper 1 repository. This report is an evidence reproduction aid, not a clinical validation report.</footer></body></html>"""
    if errors:
        return False, errors
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return True, []


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce Paper 1 evidence and generate an HTML report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent, help="Repository root")
    parser.add_argument("--output", type=Path, default=Path("reproduction_report.html"), help="HTML output path")
    parser.add_argument("--verify-only", action="store_true", help="Validate artifacts without writing HTML")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    if args.verify_only:
        probe = output.with_name(output.stem + ".verification.html")
        ok, errors = make_report(root, probe)
        if probe.exists():
            probe.unlink()
    else:
        ok, errors = make_report(root, output)
    if ok:
        print("PASS: verified evidence inputs and generated report" if not args.verify_only else "PASS: verified evidence inputs")
        if not args.verify_only:
            print(f"Report: {output}")
        return 0
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
