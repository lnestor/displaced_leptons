#!/usr/bin/env python3
"""
Query XSDB for cross-sections and update source + built dataset JSON files.

Run from ~/leptons on lxplus (requires CERN network access to xsdb-temp.app.cern.ch):

    python scripts/datasets/fill_xsec.py
    python scripts/datasets/fill_xsec.py --dry-run
    python scripts/datasets/fill_xsec.py --skip-signal
"""

import argparse
import json
import sys
from pathlib import Path

import requests

XSDB_URL = "https://xsdb-temp.app.cern.ch/api/search"
SOURCES_DIR = Path("datasets/sources")
BUILT_DIR = Path("datasets/built")


def query_xsdb(process_name: str) -> float | None:
    try:
        response = requests.post(XSDB_URL, json={"process_name": process_name}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0]["cross_section"])
        return None
    except Exception as e:
        print(f"  ERROR querying XSDB for {process_name!r}: {e}", file=sys.stderr)
        return None


def extract_process_name(das_name: str) -> str:
    return das_name.strip("/").split("/")[0]


def is_signal(process_name: str) -> bool:
    return process_name.startswith("DisplacedSUSY")


def update_source_file(path: Path, xsec_map: dict[str, float], dry_run: bool) -> int:
    with open(path) as f:
        data = json.load(f)

    updated = 0
    for sample_name, sample in data.items():
        process_name = extract_process_name(sample["files"][0]["das_names"][0])
        xsec = xsec_map.get(process_name)
        if xsec is None:
            continue
        for file_entry in sample["files"]:
            if file_entry["metadata"].get("xsec") != xsec:
                file_entry["metadata"]["xsec"] = xsec
                updated += 1

    if updated and not dry_run:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        f.write("\n")

    return updated


def update_built_file(path: Path, xsec: float, dry_run: bool) -> int:
    with open(path) as f:
        data = json.load(f)

    updated = 0
    for entry in data.values():
        meta = entry.get("metadata", {})
        xsec_str = str(xsec)
        if meta.get("xsec") != xsec_str:
            meta["xsec"] = xsec_str
            updated += 1

    if updated and not dry_run:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing any files")
    parser.add_argument("--skip-signal", action="store_true",
                        help="Skip signal samples (DisplacedSUSY) entirely")
    parser.add_argument("--sources-dir", type=Path, default=SOURCES_DIR,
                        help=f"Directory containing source JSON files (default: {SOURCES_DIR})")
    parser.add_argument("--built-dir", type=Path, default=BUILT_DIR,
                        help=f"Directory containing built JSON files (default: {BUILT_DIR})")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    source_files = sorted(args.sources_dir.glob("*.json"))
    if not source_files:
        print(f"No JSON files found in {args.sources_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect all unique process names across all source files
    process_names: dict[str, str] = {}  # process_name -> built json_output path
    for source_path in source_files:
        with open(source_path) as f:
            data = json.load(f)
        for sample in data.values():
            process_name = extract_process_name(sample["files"][0]["das_names"][0])
            process_names[process_name] = sample["json_output"]

    # Query XSDB for each unique process name
    xsec_map: dict[str, float] = {}
    print(f"Querying XSDB for {len(process_names)} processes...\n")
    for process_name, built_path in sorted(process_names.items()):
        if is_signal(process_name):
            if args.skip_signal:
                print(f"  SKIP (signal)  {process_name}")
            else:
                print(f"  SKIP (signal, not in XSDB)  {process_name}")
            continue

        xsec = query_xsdb(process_name)
        if xsec is not None:
            print(f"  FOUND  {xsec:>14.6g} pb  {process_name}")
            xsec_map[process_name] = xsec
        else:
            print(f"  NOT FOUND      {'':14}  {process_name}")

    if not xsec_map:
        print("\nNo cross-sections found. Nothing to update.")
        return

    print(f"\nFound xsec for {len(xsec_map)}/{len(process_names) - sum(is_signal(p) for p in process_names)} non-signal processes.\n")

    # Update source files
    print("Updating source files...")
    for source_path in source_files:
        n = update_source_file(source_path, xsec_map, args.dry_run)
        if n:
            tag = "(dry run) " if args.dry_run else ""
            print(f"  {tag}updated {n} entries in {source_path}")

    # Update built files
    print("\nUpdating built files...")
    for process_name, built_relative in process_names.items():
        xsec = xsec_map.get(process_name)
        if xsec is None:
            continue
        built_path = args.built_dir / Path(built_relative).name
        if not built_path.exists():
            print(f"  WARNING: built file not found: {built_path}")
            continue
        n = update_built_file(built_path, xsec, args.dry_run)
        if n:
            tag = "(dry run) " if args.dry_run else ""
            print(f"  {tag}updated {n} entries in {built_path.name}")

    if args.dry_run:
        print("\nDry run complete — rerun without --dry-run to apply changes.")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
