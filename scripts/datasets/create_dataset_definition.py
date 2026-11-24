import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess

from catalog import DatasetCatalog
from pocket_coffea.utils.rucio import get_dataset_files_replicas
import uproot

EOS_SERVER = "root://cmseos.fnal.gov"


def _dasgoclient_json(query):
    result = subprocess.run(
        ["dasgoclient", "-query", query, "-json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"ERROR: dasgoclient error for query '{query}'")
        exit(1)

    return json.loads(result.stdout)


def get_summary(dataset_def):
    records = _dasgoclient_json(f"summary dataset={dataset_def.nanoaod}")
    summaries = [r for record in records for r in record["summary"]]
    nevents = sum(r["nevents"] for r in summaries)
    size = sum(r["file_size"] for r in summaries)
    return nevents, size


def get_files_redirector(dataset_def, redirector):
    records = _dasgoclient_json(f"file dataset={dataset_def.nanoaod}")
    return [redirector + r["name"] for record in records for r in record["file"]]


def get_files_sites(dataset_def):
    files, _, _ = get_dataset_files_replicas(
        dataset_def.nanoaod,
        sort="geoip",
        mode="first",
        partial_allowed=False,
    )
    return files


def get_files(dataset_def, mode, redirector):
    if mode == "sites":
        return get_files_sites(dataset_def)
    return get_files_redirector(dataset_def, redirector)


def list_eos_files(eos_dir):
    result = subprocess.run(["xrdfs", EOS_SERVER, "ls", "-l", eos_dir], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"xrdfs ls -l {eos_dir} failed: {result.stderr.strip()}")

    files, size = [], 0
    for line in result.stdout.splitlines():
        fields = line.split()
        if fields and fields[-1].endswith(".root"):
            files.append(f"{EOS_SERVER}/{fields[-1]}")
            size += int(fields[3])
    return files, size


def count_events(file):
    with uproot.open(f"{file}:Runs") as tree:
        return int(tree["genEventCount"].array(library="np").sum())


def get_eos_dataset(dataset_def, workers):
    files, size = list_eos_files(dataset_def.nanoaod)
    if not files:
        raise RuntimeError(f"no ROOT files in {dataset_def.nanoaod}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        nevents = sum(executor.map(count_events, files))
    return files, nevents, size


def load(output_path):
    if not os.path.exists(output_path):
        return {}

    with open(output_path) as f:
        return json.load(f)


def save(output_path, data):
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", nargs="+")
    parser.add_argument("--years", nargs="+")
    parser.add_argument("--definition-path", default="datasets/sources/datasets.yaml")
    parser.add_argument("--output-dir", default="datasets/central")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--redirector", default="root://cmsxrootd.fnal.gov/")
    parser.add_argument("--mode", choices=["redirector", "sites"], default="redirector")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    # WARNING: This won't work for data because I was combining datasets, i.e. EGamma0 and EGamma1 in one key

    catalog = DatasetCatalog(args.definition_path)
    dataset_defs = catalog.get(sample=args.samples, year=args.years)

    os.makedirs(args.output_dir, exist_ok=True)

    failures = []

    for d in dataset_defs:
        output_path = f"{args.output_dir}/{d.sample}.json"
        data = load(output_path)

        if d.key in data and not args.overwrite:
            print(f"Skipping '{d.key}' -- already exists in {output_path} (use --overwrite to replace)")
            continue

        try:
            if d.type == "eos":
                print(f"Reading EOS files for '{d.key}'...")
                files, nevents, size = get_eos_dataset(d, args.workers)
            else:
                print(f"Querying DAS for '{d.key}'...")
                nevents, size = get_summary(d)
                files = get_files(d, args.mode, args.redirector)
        except Exception as e:
            print(f"ERROR: failed to resolve files for '{d.key}': {e}")
            failures.append(d.key)
            continue

        metadata = {
            "das_names": f"['{d.nanoaod}']",
            "sample": d.sample,
            "year": d.year,
            "isMC": d.is_mc,
            "nevents": nevents,
            "size": size,
        }

        if d.is_mc:
            metadata["xsec"] = d.xsec
        else:
            metadata["era"] = d.era
            metadata["primaryDataset"] = d.sample

        data[d.key] = {
            "metadata": {k: str(v) for k, v in metadata.items()},
            "files": files,
        }

        save(output_path, data)

    if failures:
        print(f"\nFailed to resolve files for {len(failures)} dataset(s):")
        for key in failures:
            print(f"  - {key}")


if __name__ == "__main__":
    main()
