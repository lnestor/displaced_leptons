#!/usr/bin/env python3
"""
Generate a pocket-coffea dataset definition JSON from a plain list of DAS paths.

Usage:
    python generate_dataset_definition.py das_names.txt -o datasets.json

Each line in the input file should be a full DAS path, e.g.:
    /DisplacedSUSY_stopToLD_M_200_1mm_TuneCP5_13TeV-madgraph-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM

Blank lines and lines starting with # are ignored.

After generating the source JSON, run the following:
    pocket-coffea build-datasets --cfg datasets.json --overwrite
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def extract_year(das_name: str) -> str:
    # TODO: clean this up
    """Mirror pocket-coffea's DataDiscoveryCLI.extract_year_from_dataset_name."""

    if "RunIISummer20UL16NanoAODAPV" in das_name:
        return "2016_PreVFP"
    elif "RunIISummer20UL16NanoAOD" in das_name:
        return "2016_PostVFP"

    match = re.search(r'/([^/]+)NanoAOD', das_name)
    if not match:
        raise ValueError(f"Cannot extract year from DAS name: {das_name!r}")
    campaign = match.group(1)
    mapping = {
        # 'RunIISummer20UL16NanoAODAPV': '2016_PreVFP',
        # 'RunIISummer20UL16NanoAOD':    '2016_PostVFP',
        'RunIISummer20UL17':           '2017',
        'RunIISummer20UL18':           '2018',
        'Run3Summer22EE':              '2022_postEE',
        'Run3Summer22':                '2022_preEE',
        'Run3Summer23BPix':            '2023_postBPix',
        'Run3Summer23':                '2023_preBPix',
        'RunIII2024Summer24':          '2024',
    }
    if campaign not in mapping:
        raise ValueError(f"Unrecognised campaign string {campaign!r} in: {das_name!r}")
    return mapping[campaign]


def is_mc(das_name: str) -> bool:
    """Mirror pocket-coffea's DataDiscoveryCLI.is_mc_dataset."""
    return 'SIM' in das_name.split('/')[-1]


def parse_das_name(das_name: str) -> tuple[str, str, bool]:
    parts = das_name.strip().strip('/').split('/')
    if len(parts) != 3:
        raise ValueError(f"Expected 3 path components, got {len(parts)}: {das_name!r}")
    sample_name = parts[0]
    year = extract_year(das_name)
    mc = is_mc(das_name)
    return sample_name, year, mc


def build_source_json(das_names: list[str], output_dir: str = "datasets/built") -> dict:
    grouped: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)
    for das_name in das_names:
        sample_name, year, mc = parse_das_name(das_name)
        grouped[sample_name].append((das_name, year, mc))

    result = {}
    for sample_name, entries in sorted(grouped.items()):
        files = []
        for das_name, year, mc in sorted(entries, key=lambda x: x[1]):
            files.append({
                "das_names": [das_name],
                "metadata": {
                    "year": year,
                    "isMC": mc,
                    "xsec": 1.0,
                },
            })
        result[sample_name] = {
            "sample": sample_name,
            "json_output": f"{output_dir}/{sample_name}.json",
            "files": files,
        }
    return result


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "input",
        help="Text file with one DAS path per line (use - for stdin)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON file (default: print to stdout)",
    )
    parser.add_argument(
        "--output-dir",
        default="datasets/built",
        help="Directory prefix used in json_output paths (default: datasets/built)",
    )
    args = parser.parse_args()

    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text()
    das_names = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not das_names:
        print("No DAS names found in input.", file=sys.stderr)
        sys.exit(1)

    source = build_source_json(das_names, output_dir=args.output_dir)
    output_json = json.dumps(source, indent=2)

    if args.output:
        Path(args.output).write_text(output_json + "\n")
        print(f"Wrote {len(source)} sample(s) to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
