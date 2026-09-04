import argparse
import json
import os
import subprocess

from catalog import DatasetCatalog
from pocket_coffea.utils.rucio import get_dataset_files_replicas


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

        print(f"Querying DAS for '{d.key}'...")

        nevents, size = get_summary(d)
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

        try:
            files = get_files(d, args.mode, args.redirector)
        except Exception as e:
            print(f"ERROR: failed to resolve files for '{d.key}': {e}")
            failures.append(d.key)
            continue

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
