"""Download and extract Stanford Puffer's official fake sample dataset.

Run from the project root:
    python src/download_puffer_sample.py

The official documentation recommends starting with this fake sample because a
single day of real Puffer data can be several GB.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://storage.googleapis.com/puffer-data-release/puffer-fake-sample.tar.gz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if destination not in target.parents and target != destination:
            raise ValueError(f"Unsafe path in archive: {member.name}")
    archive.extractall(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output-dir", default="data/raw/puffer_fake_sample")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    archive_path = output_dir.parent / "puffer-fake-sample.tar.gz"

    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        print(f"Sample already exists at {output_dir}. Use --force to replace it.")
        return

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if args.force:
        shutil.rmtree(output_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)

    print(f"Downloading {args.url}")
    try:
        urllib.request.urlretrieve(args.url, archive_path)
    except Exception as exc:
        raise SystemExit(
            "Download failed. Open the official Puffer Data Description page, "
            "download 'fake data' manually, place puffer-fake-sample.tar.gz in "
            "data/raw/, then rerun with --url file:data/raw/puffer-fake-sample.tar.gz. "
            f"Original error: {exc}"
        ) from exc

    print(f"Downloaded {archive_path.stat().st_size:,} bytes")
    print(f"SHA-256: {sha256(archive_path)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        safe_extract(archive, output_dir)

    csvs = sorted(output_dir.rglob("*.csv"))
    print(f"Extracted {len(csvs)} CSV files to {output_dir}")
    for path in csvs[:20]:
        print(" -", path.relative_to(output_dir))


if __name__ == "__main__":
    main()
