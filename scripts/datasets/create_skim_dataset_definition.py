import argparse
import json
import os

import coffea.util

import scripts.eos_helper as eos_helper


def _load_central_metadata(central_dir):
    metadata_by_dataset = {}
    for fname in os.listdir(central_dir):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(central_dir, fname)) as f:
            data = json.load(f)
        for key, entry in data.items():
            if key in metadata_by_dataset:
                print(f"WARNING: dataset '{key}' found in multiple central dataset files")
            metadata_by_dataset[key] = entry["metadata"]
    return metadata_by_dataset


def _is_mc(metadata):
    return metadata.get("isMC") in (True, "True", "true")


def _load(output_path):
    if not os.path.exists(output_path):
        return {}
    with open(output_path) as f:
        return json.load(f)


def _save(output_path, data):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)


def build_definition(dataset_key, channel_dir, central_metadata, genweights):
    if dataset_key not in central_metadata:
        print(f"SKIP '{dataset_key}': not found in any central dataset definition")
        return None

    metadata = dict(central_metadata[dataset_key])

    root_files = eos_helper.try_get_root_files(f"{channel_dir}/{dataset_key}")
    if not root_files:
        print(f"SKIP '{dataset_key}': no ROOT files found on EOS")
        return None

    if _is_mc(metadata):
        sum_genweights = genweights.get("sum_genweights", {})
        sum_signof_genweights = genweights.get("sum_signOf_genweights", {})

        if dataset_key not in sum_genweights:
            print(f"SKIP '{dataset_key}': isMC but missing from --genweights-file")
            return None

        metadata["sum_genweights"] = float(sum_genweights[dataset_key])
        if dataset_key in sum_signof_genweights:
            metadata["sum_signOf_genweights"] = float(sum_signof_genweights[dataset_key])

    metadata["isSkim"] = "True"

    return {"metadata": metadata, "files": root_files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eos-path", default="root://cmseos.fnal.gov//store/user/lnestor/skims")
    parser.add_argument("--genweights-file", required=True)
    parser.add_argument("--central-dir", default="datasets/central")
    parser.add_argument("--output-dir", default="datasets/skims")
    parser.add_argument("--channels", nargs="+", default=None)
    parser.add_argument("--datasets", nargs="+", default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    central_metadata = _load_central_metadata(args.central_dir)
    genweights = coffea.util.load(args.genweights_file)

    channels = args.channels
    if channels is None:
        entries = eos_helper.list_dir_entries(args.eos_path)
        if entries is None:
            print(f"ERROR: could not list {args.eos_path}")
            return
        channels = [os.path.basename(e) for e in entries]

    for channel in channels:
        channel_dir = f"{args.eos_path}/{channel}"

        dataset_keys = args.datasets
        if dataset_keys is None:
            entries = eos_helper.list_dir_entries(channel_dir)
            if entries is None:
                print(f"WARNING: could not list {channel_dir}, skipping channel '{channel}'")
                continue
            dataset_keys = [os.path.basename(e) for e in entries]

        output_by_path = {}

        for dataset_key in dataset_keys:
            definition = build_definition(dataset_key, channel_dir, central_metadata, genweights)
            if definition is None:
                continue

            sample = definition["metadata"]["sample"]
            output_path = f"{args.output_dir}/{channel}/{sample}.json"
            data = output_by_path.setdefault(output_path, _load(output_path))

            if dataset_key in data and not args.overwrite:
                print(f"Skipping '{dataset_key}' -- already exists in {output_path} (use --overwrite to replace)")
                continue

            data[dataset_key] = definition
            print(f"'{dataset_key}' -> {output_path}")

        for output_path, data in output_by_path.items():
            _save(output_path, data)


if __name__ == "__main__":
    main()
