#!/usr/bin/env python3
"""
Populate cross-section values in source and built dataset JSON files.

Values in XSEC_MAP are keyed on the bare process name (first component of the
DAS path, stripped of year/campaign info) so one entry covers all years.
Entries set to None are skipped.

Run from ~/leptons:

    python scripts/datasets/replace_xsec.py
    python scripts/datasets/replace_xsec.py --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

SOURCES_DIR = Path("datasets/sources")
BUILT_DIR = Path("datasets/built")

# Cross sections in pb. Keyed on bare process name (DAS path component 0).
# fmt: off
XSEC_MAP = {
    "DYJetsToLL_M-10to50_TuneCP5_13TeV-madgraphMLM-pythia8":                       15910.0,
    "DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8":                            5379.0,
    "QCD_Pt-1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                                1.085,
    "QCD_Pt-120To170_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        21280.0,
    "QCD_Pt-120to170_EMEnriched_TuneCP5_13TeV-pythia8":                           66600.0,
    "QCD_Pt-15To20_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        2800000.0,
    "QCD_Pt-15to20_EMEnriched_TuneCP5_13TeV-pythia8":                           1335000.0,
    "QCD_Pt-170To300_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        7000.0,
    "QCD_Pt-170to300_EMEnriched_TuneCP5_13TeV-pythia8":                          16620.0,
    "QCD_Pt-20To30_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        2527000.0,
    "QCD_Pt-20to30_EMEnriched_TuneCP5_13TeV-pythia8":                           4787000.0,
    "QCD_Pt-300To470_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                          622.6,
    "QCD_Pt-300toInf_EMEnriched_TuneCP5_13TeV-pythia8":                            1101.0,
    "QCD_Pt-30To50_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        1367000.0,
    "QCD_Pt-30to50_EMEnriched_TuneCP5_13TeV-pythia8":                           6401000.0,
    "QCD_Pt-470To600_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                           58.9,
    "QCD_Pt-50To80_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                         381700.0,
    "QCD_Pt-50to80_EMEnriched_TuneCP5_13TeV-pythia8":                           1993000.0,
    "QCD_Pt-600To800_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                           18.12,
    "QCD_Pt-800To1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                           3.318,
    "QCD_Pt-80To120_MuEnrichedPt5_TuneCP5_13TeV-pythia8":                        87740.0,
    "QCD_Pt-80to120_EMEnriched_TuneCP5_13TeV-pythia8":                          364000.0,
    "ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8":                    3.549,
    "ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8":  67.93,
    "ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8":     113.4,
    "ST_tW_antitop_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8":           32.51,
    "ST_tW_top_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8":               32.45,
    "TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8":                                         72.15,   # 687.1 * 0.105
    "TTToHadronic_TuneCP5_13TeV-powheg-pythia8":                                     314.0,   # 687.1 * 0.457
    "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8":                                 300.9,   # 687.1 * 0.438
    "WW_TuneCP5_13TeV-pythia8":                                                       77.25,
    "WZ_TuneCP5_13TeV-pythia8":                                                       27.55,
    "ZZ_TuneCP5_13TeV-pythia8":                                                       12.23,
}
# fmt: on


def extract_process_name(das_name):
    return das_name.strip("/").split("/")[0]


def is_signal(process_name):
    return process_name.startswith("DisplacedSUSY")


def update_source_file(path, dry_run):
    with open(path) as f:
        data = json.load(f)

    updated = 0
    for sample in data.values():
        process_name = extract_process_name(sample["files"][0]["das_names"][0])
        if is_signal(process_name):
            continue
        xsec = XSEC_MAP.get(process_name)
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


def update_built_file(path, xsec, dry_run):
    with open(path) as f:
        data = json.load(f)

    xsec_str = str(xsec)
    updated = 0
    for entry in data.values():
        meta = entry.get("metadata", {})
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
    parser.add_argument("--sources-dir", type=Path, default=SOURCES_DIR,
                        help=f"Directory containing source JSON files (default: {SOURCES_DIR})")
    parser.add_argument("--built-dir", type=Path, default=BUILT_DIR,
                        help=f"Directory containing built JSON files (default: {BUILT_DIR})")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    active_xsec = {k: v for k, v in XSEC_MAP.items() if v is not None}
    if not active_xsec:
        print("No cross-sections set in XSEC_MAP. Fill in values and re-run.", file=sys.stderr)
        sys.exit(1)

    source_files = sorted(args.sources_dir.glob("*.json"))
    if not source_files:
        print(f"No JSON files found in {args.sources_dir}", file=sys.stderr)
        sys.exit(1)

    # Update source files
    print("Updating source files...")
    for source_path in source_files:
        n = update_source_file(source_path, args.dry_run)
        if n:
            tag = "(dry run) " if args.dry_run else ""
            print(f"  {tag}updated {n} entries in {source_path.name}")

    # Collect process_name -> built path from source files, then update built files
    print("\nUpdating built files...")
    process_to_built = {}
    for source_path in source_files:
        with open(source_path) as f:
            data = json.load(f)
        for sample in data.values():
            process_name = extract_process_name(sample["files"][0]["das_names"][0])
            process_to_built[process_name] = Path(sample["json_output"]).name

    for process_name, built_name in sorted(process_to_built.items()):
        xsec = active_xsec.get(process_name)
        if xsec is None:
            continue
        built_path = args.built_dir / built_name
        if not built_path.exists():
            print(f"  WARNING: built file not found: {built_path}")
            continue
        n = update_built_file(built_path, xsec, args.dry_run)
        if n:
            tag = "(dry run) " if args.dry_run else ""
            print(f"  {tag}updated {n} entries in {built_name}")

    if args.dry_run:
        print("\nDry run complete — rerun without --dry-run to apply changes.")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
