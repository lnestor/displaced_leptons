import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import uproot

sys.path.append("scripts")
import crab_helper
import eos_helper

EOS_REDIRECTOR = "root://cmseos.fnal.gov"


def _get_nevents_one(xrootd_path):
    try:
        return next(uproot.num_entries(f"{xrootd_path}:Events"))[-1]
    except Exception as e:
        print(f"ERROR reading {xrootd_path}: {e}")
        return 0


def get_nevents(files):
    with ThreadPoolExecutor(max_workers=20) as executor:
        return sum(executor.map(_get_nevents_one, files))


def get_size(files):
    with ThreadPoolExecutor(max_workers=20) as executor:
        return sum(executor.map(eos_helper.get_file_size, files))


def check_output(key, output, force):
    if os.path.exists(output):
        with open(output) as f:
            data = json.load(f)
        if key in data and not force:
            print(f"ERROR: key '{key}' already exists in {output}. Use --force to overwrite.")
            sys.exit(1)


def save(key, definition, output):
    if os.path.exists(output):
        with open(output) as f:
            data = json.load(f)
    else:
        data = {}
    data[key] = definition
    with open(output, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Written '{key}' to {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crab-dir")
    parser.add_argument("--eos-dir")
    parser.add_argument("--output", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.crab_dir and not args.eos_dir:
        print("ERROR: must provide --crab-dir or --eos-dir")
        sys.exit(1)

    check_output(args.key, args.output, args.force)

    if args.crab_dir:
        lfns = crab_helper.get_crab_output_lfns(args.crab_dir)
        files = [f"{EOS_REDIRECTOR}/{lfn}" for lfn in lfns]
    else:
        files = eos_helper.get_root_files(args.eos_dir)

    if not files:
        print("ERROR: no files found")
        sys.exit(1)
    print(f"Found {len(files)} files")

    with open(args.template) as f:
        template = json.load(f)
    if args.key not in template:
        keys = "\n  ".join(template.keys())
        print(f"ERROR: key '{args.key}' not found in {args.template}. Available keys:\n  {keys}")
        sys.exit(1)
    definition = template[args.key]

    print("Counting events...")
    print("Getting file sizes...")
    definition["metadata"]["nevents"] = str(get_nevents(files))
    definition["metadata"]["size"] = str(get_size(files))
    definition["files"] = files

    save(args.key, definition, args.output)


if __name__ == "__main__":
    main()
