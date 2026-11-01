import csv
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path.cwd()
PROCESSED = ROOT / "data/processed"
ASSEMBLIES = ROOT / "data/assemblies/automated"
OUTPUT = PROCESSED / "ecoli_mlst_parallel.tsv"
FAILED = PROCESSED / "ecoli_mlst_parallel_failures.tsv"
MLST = "/home/faizan/miniforge3/envs/ecoli-amr/bin/mlst"

existing_files = [
    "ecoli_mlst_pilot.tsv",
    "ecoli_mlst_batch_001.tsv",
    "ecoli_mlst_automated.tsv",
    "ecoli_mlst_parallel.tsv",
]

completed = set()
for name in existing_files:
    path = PROCESSED / name
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                completed.add(Path(line.split("\t")[0]).name.removesuffix(".fna.gz"))

with open(PROCESSED / "ecoli_mlst_pending.csv") as handle:
    pending = [
        row["Accession"]
        for row in csv.DictReader(handle)
        if row["Accession"] not in completed
    ]

print(f"Already completed: {len(completed)}", flush=True)
print(f"Pending MLST: {len(pending)}", flush=True)
print("Parallel workers: 3", flush=True)

def process(accession):
    path = ASSEMBLIES / f"{accession}.fna.gz"
    if not path.is_file():
        return accession, None, "Missing cached assembly"

    result = subprocess.run(
        [MLST, "--quiet", "--scheme", "ecoli_achtman_4", str(path)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    if result.returncode != 0:
        return accession, None, result.stderr.strip()[:500]

    lines = [x for x in result.stdout.splitlines() if x.strip()]
    if len(lines) != 1:
        return accession, None, f"Expected one MLST row, got {len(lines)}"

    fields = lines[0].split("\t")
    if (
        len(fields) != 10
        or Path(fields[0]).name.removesuffix(".fna.gz") != accession
        or fields[1] != "ecoli_achtman_4"
        or not all(fields[2:])
    ):
        return accession, None, "Unexpected MLST output format"

    return accession, lines[0], None

with (
    open(OUTPUT, "a", buffering=1) as out,
    open(FAILED, "a", buffering=1) as errors,
    ThreadPoolExecutor(max_workers=3) as pool,
):
    futures = [pool.submit(process, accession) for accession in pending]
    success = 0
    failed = 0

    for i, future in enumerate(as_completed(futures), 1):
        accession, result, error = future.result()

        if error:
            errors.write(f"{accession}\t{error}\n")
            errors.flush()
            failed += 1
        else:
            out.write(result + "\n")
            out.flush()
            os.fsync(out.fileno())
            success += 1

        if i % 50 == 0 or i == len(futures):
            print(
                f"Processed {i}/{len(futures)} | "
                f"Saved: {success} | Failed: {failed}",
                flush=True,
            )

print(f"FINISHED | Saved: {success} | Failed: {failed}")
