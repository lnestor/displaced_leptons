import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import uproot
from scripts import crab_helper, eos_helper

EOS_REDIRECTOR = "root://cmseos.fnal.gov"


def get_lumi_file_map(files):
    def _get_lumi_file_map_one(xrootd_path):
        try:
            arrays = uproot.open(f"{xrootd_path}:supplementTree/Events").arrays(["run", "luminosityBlock"])
            return xrootd_path, set(zip(arrays["run"].tolist(), arrays["luminosityBlock"].tolist()))
        except Exception as e:
            print(f"ERROR reading {xrootd_path}: {e}")
            return xrootd_path, set()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(_get_lumi_file_map_one, files)

    index = {}
    for file, run_lumis in results:
        for run_lumi in run_lumis:
            if run_lumi in index and index[run_lumi] != file:
                run, lumi = run_lumi
                print(f"ERROR: run {run}, lumi {lumi} found in both {index[run_lumi]} and {file}")
                exit(1)
            index[run_lumi] = file
    return index


def get_central_runs_lumis(dataset, runs):
    def _get_central_run_one(dataset, run, retries=3, delay=5):
        for attempt in range(1, retries + 1):
            result = subprocess.run(
                ["dasgoclient", "-query", f"file,lumi dataset={dataset} run={run}", "-json"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                break
            print(f"WARNING: dasgoclient query failed for run {run} (attempt {attempt}/{retries}): {result.stderr.strip()}")
            if attempt < retries:
                time.sleep(delay)
        else:
            print(f"ERROR: dasgoclient query failed for run {run} after {retries} attempts")
            sys.exit(1)

        files = {}
        for record in json.loads(result.stdout):
            file = record["file"][0]["name"]
            run_lumis = [(run, lumi) for lumi in record["lumi"][0]["number"]]
            files.setdefault(file, []).extend(run_lumis)
        return files

    index = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(lambda run: _get_central_run_one(dataset, run), sorted(runs))
    for files in results:
        for file, run_lumis in files.items():
            index.setdefault(file, []).extend(run_lumis)
    return index


def get_supplement_version(files):
    def _get_version_one(xrootd_path):
        try:
            arrays = uproot.open(f"{xrootd_path}:supplementTree/Runs").arrays(["version"])
            return xrootd_path, set(arrays["version"].tolist())
        except Exception as e:
            print(f"ERROR reading {xrootd_path}: {e}")
            return xrootd_path, set()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(_get_version_one, files)

    versions = set()
    for _, file_versions in results:
        versions |= file_versions

    if len(versions) != 1:
        print(f"ERROR: supplement files have inconsistent versions: {sorted(versions)}")
        sys.exit(1)

    return versions.pop()


def merge_definitions(existing, new):
    existing_meta = existing["metadata"]
    new_meta = new["metadata"]

    for field in ("sample", "year", "era", "version"):
        if existing_meta[field] != new_meta[field]:
            print(
                f"ERROR: cannot append -- existing '{field}' ({existing_meta[field]!r}) "
                f"does not match new '{field}' ({new_meta[field]!r})"
            )
            sys.exit(1)

    existing_datasets = existing_meta["dataset"]
    if not isinstance(existing_datasets, list):
        existing_datasets = [existing_datasets]
    if new_meta["dataset"] not in existing_datasets:
        existing_datasets = existing_datasets + [new_meta["dataset"]]

    for central_file, supp_files in new["files"].items():
        if central_file in existing["files"] and existing["files"][central_file] != supp_files:
            print(
                f"ERROR: cannot append -- central file '{central_file}' already has a "
                f"different supplement mapping in the existing definition"
            )
            sys.exit(1)

    merged_files = dict(existing["files"])
    merged_files.update(new["files"])

    return {
        "metadata": {**existing_meta, "dataset": existing_datasets},
        "files": merged_files,
    }


def save(key, definition, output, overwrite, append):
    if os.path.exists(output):
        with open(output) as f:
            data = json.load(f)
    else:
        data = {}

    if key in data and not overwrite and not append:
        print(f"ERROR: key '{key}' already exists in {output}. Use --overwrite to replace it or --append to merge into it.")
        sys.exit(1)

    if key in data and append:
        definition = merge_definitions(data[key], definition)

    data[key] = definition
    with open(output, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Written '{key}' to {output}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--crab-dir")
    group.add_argument("--eos-dir")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--year", required=True)
    parser.add_argument("--era", required=True)
    write_group = parser.add_mutually_exclusive_group()
    write_group.add_argument("--overwrite", action="store_true", help="Replace an existing key")
    write_group.add_argument("--append", action="store_true", help="Merge into an existing key (e.g. combining EGamma0/EGamma1 into one dataset)")
    args = parser.parse_args()

    if args.crab_dir:
        lfns = crab_helper.get_crab_output_lfns(args.crab_dir)
        files = [f"{EOS_REDIRECTOR}/{lfn}" for lfn in lfns]
    else:
        files = eos_helper.get_root_files(args.eos_dir, recursive=True)

    if not files:
        print("ERROR: not files found")
        exit(1)
    print(f"Found {len(files)} files")

    print("Reading runs/lumis from supplement files...")
    supp_lumis_to_file = get_lumi_file_map(files)
    print(f"Found {len(supp_lumis_to_file)} unique run/lumi pairs")

    print("Reading run/lumis of central files via dasgoclient...")
    runs = {run for run, _ in supp_lumis_to_file}
    central_file_to_lumis = get_central_runs_lumis(args.dataset, runs)

    print("Reading supplement version...")
    version = get_supplement_version(files)
    print(f"Supplement version: {version}")

    print("Matching central files to supplement files...")
    file_mapping = {}
    for central_file, central_lumis in central_file_to_lumis.items():
        # A lumi with no entry has no supplement event, e.g. it failed the
        # trigger filter -- not an error, just skip it.
        supp_files = sorted(set(
            supp_lumis_to_file[l] for l in central_lumis if l in supp_lumis_to_file
        ))
        file_mapping[central_file] = supp_files

    definition = {
        "metadata": {
            "dataset": args.dataset,
            "sample": args.sample,
            "year": args.year,
            "era": args.era,
            "version": version
        },
        "files": file_mapping
    }

    save(args.key, definition, args.output, args.overwrite, args.append)


if __name__ == "__main__":
    main()
