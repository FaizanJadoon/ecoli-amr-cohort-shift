
import argparse
import csv
import gzip
import re
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/processed/ecoli_mlst_assembly_manifest.csv"
DOWNLOAD_DIR = ROOT / "data/assemblies/automated"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Ecoli-AMR-Research/1.0"
})


def validate_gzip(path):
    """Verify that a downloaded gzip file is readable."""
    try:
        with gzip.open(path, "rb") as handle:
            while handle.read(1024 * 1024):
                pass
        return True
    except (OSError, EOFError):
        return False


def download_genome(accession):
    """Download one assembly from NCBI FTP."""

    destination = DOWNLOAD_DIR / f"{accession}.fna.gz"

    if destination.exists():
        if destination.stat().st_size > 0:
            return destination
        destination.unlink()

    prefix, versioned_id = accession.split("_")
    digits = versioned_id.split(".")[0]

    base_url = (
        f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{prefix}/"
        f"{digits[:3]}/{digits[3:6]}/{digits[6:9]}"
    )

    response = session.get(base_url + "/", timeout=60)
    response.raise_for_status()

    pattern = re.compile(
        rf'href="({re.escape(accession)}_[^"/]+/)"'
    )
    match = pattern.search(response.text)

    if not match:
        raise RuntimeError(f"Assembly directory not found: {accession}")

    folder = match.group(1).rstrip("/")
    url = f"{base_url}/{folder}/{folder}_genomic.fna.gz"

    temporary = destination.with_name(destination.name + ".part")

    try:
        with session.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()

            with open(temporary, "wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)

        if not validate_gzip(temporary):
            raise RuntimeError(f"Corrupted download: {accession}")

        temporary.replace(destination)

    finally:
        temporary.unlink(missing_ok=True)

    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    with open(MANIFEST, newline="", encoding="utf-8-sig") as handle:
        manifest = list(csv.DictReader(handle))

    existing_results = [
        ROOT / "data/processed/ecoli_mlst_pilot.tsv",
        ROOT / "data/processed/ecoli_mlst_batch_001.tsv",
        ROOT / "data/processed/ecoli_mlst_automated.tsv",
    ]

    completed = set()

    for result_file in existing_results:
        if result_file.exists():
            with open(result_file, encoding="utf-8") as handle:
                for line in handle:
                    fields = line.rstrip("\n").split("\t")
                    if len(fields) >= 10:
                        accession = Path(fields[0]).name.removesuffix(".fna.gz")
                        completed.add(accession)

    pending = [
        row["Accession"]
        for row in manifest
        if row["Accession"] not in completed
    ]

    selected = pending if args.limit == 0 else pending[:args.limit]

    print(f"Total assemblies: {len(manifest)}")
    print(f"Previously typed: {len(completed)}")
    print(f"Downloading: {len(selected)}")

    
    # Process genomes in batches of 100.
    batch_size = 100
    failures_file = ROOT / "data/processed/ecoli_mlst_failures.log"

    for start in range(0, len(selected), batch_size):
        batch = selected[start:start + batch_size]
        downloaded = []

        for index, accession in enumerate(batch, start + 1):
            for attempt in range(1, 4):
                try:
                    path = download_genome(accession)
                    downloaded.append(path)
                    print(
                        f"[{index}/{len(selected)}] OK: {accession}",
                        flush=True,
                    )
                    break

                except Exception as error:
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                    else:
                        message = f"DOWNLOAD FAILED {accession}: {error}"
                        print(message, flush=True)
                        with open(failures_file, "a") as log:
                            log.write(message + "\n")

        if not downloaded:
            continue

        try:
            count = run_mlst_batch(downloaded)
            print(
                f"MLST completed: {count} results saved",
                flush=True,
            )

        except Exception as error:
            message = f"MLST BATCH FAILED: {error}"
            print(message, flush=True)

            with open(failures_file, "a") as log:
                log.write(message + "\n")



def run_mlst_batch(paths):
    """Run MLST and append validated results to the checkpoint file."""
    import subprocess
    import os

    results_file = ROOT / "data/processed/ecoli_mlst_automated.tsv"

    command = [
        "mlst",
        "--quiet",
        "--scheme",
        "ecoli_achtman_4",
        *[str(path) for path in paths],
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    lines = [
        line for line in result.stdout.splitlines()
        if line.strip()
    ]

    if len(lines) != len(paths):
        raise RuntimeError(
            f"Expected {len(paths)} results, got {len(lines)}"
        )

    expected = {path.name.removesuffix(".fna.gz") for path in paths}
    observed = set()

    for line in lines:
        fields = line.split("\t")

        if len(fields) != 10:
            raise RuntimeError(f"Invalid MLST row: {line}")

        accession = Path(fields[0]).name.removesuffix(".fna.gz")

        if (
            accession not in expected
            or accession in observed
            or fields[1] != "ecoli_achtman_4"
            or not (fields[2].isdigit() or fields[2] == "-")
            or not all(
                re.fullmatch(r"[A-Za-z0-9_]+\([~?*+-]*\d+[~?*+-]*\)|[A-Za-z0-9_]+\(-\)", allele)
                for allele in fields[3:]
            )
        ):
            raise RuntimeError(f"Incomplete or unexpected MLST result: {line}")

        observed.add(accession)

    with open(results_file, "a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    return len(lines)


if __name__ == "__main__":
    main()
