import argparse
import faulthandler
import json
import os
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from scripts import crab_helper, eos_helper
from scripts.datasets.catalog import DatasetCatalog

EOS_REDIRECTOR = "root://cmseos.fnal.gov"
# xrootd reads are network-latency bound, not CPU bound, so this can be much
# higher than a typical thread pool size without straining the LPC node.
XROOTD_WORKERS = 20

# Some supplement productions name files generically (supplement_1.root, ...)
# and need run/lumi matching to pair them with central files. Others name
# each supplement file after the central file it corresponds to, in which
# case pairing is a direct filename match -- no need to open any files.
NUMBERED_SUPPLEMENT_RE = re.compile(r"^supplement_\d+\.root$")

DATA_SAMPLES = ["EGamma", "Muon", "MuonEG", "MET"]
MC_SAMPLES = ["DY", "Diboson", "TTbar", "SingleTop", "QCDMu", "QCDEle"]
YEAR_GROUPS = {
    "2022": ["2022_preEE", "2022_postEE"],
    "2023": ["2023_preBPix", "2023_postBPix"],
}


def expand_samples(samples):
    expanded = []
    for sample in samples:
        if sample == "Data":
            expanded.extend(DATA_SAMPLES)
        elif sample == "MC":
            expanded.extend(MC_SAMPLES)
        else:
            expanded.append(sample)
    return list(set(expanded))


def expand_years(years):
    expanded = []
    for year in years:
        expanded.extend(YEAR_GROUPS.get(year, [year]))
    return list(set(expanded))


# xrootd reads for these run in their own subprocess (not just a thread): a
# stalled/unresponsive server (e.g. one that sends kXR_wait keep-alives and
# never actually times out the client) leaves a thread permanently blocked
# in the XRootD C client with no way to interrupt it. A subprocess can
# instead be killed outright by subprocess.run's timeout, so a hung read
# doesn't cost us a worker permanently and can be retried cleanly.
_LUMI_READER = """
import sys, json
import uproot
path = sys.argv[1]
try:
    with uproot.open(f"{path}:supplementTree/Events") as tree:
        arrays = tree.arrays(["run", "luminosityBlock"])
    print(json.dumps(list(zip(arrays["run"].tolist(), arrays["luminosityBlock"].tolist()))))
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
"""

_VERSION_READER = """
import sys, json
import uproot
path = sys.argv[1]
try:
    with uproot.open(f"{path}:supplementTree/Runs") as tree:
        arrays = tree.arrays(["version"])
    print(json.dumps(list(set(arrays["version"].tolist()))))
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
"""


def _read_via_subprocess(reader_script, xrootd_path, timeout=60, retries=3):
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                [sys.executable, "-c", reader_script, xrootd_path],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"WARNING: timed out reading {xrootd_path} (attempt {attempt}/{retries}), killed subprocess")
            continue
        if result.returncode != 0:
            print(f"ERROR reading {xrootd_path}: {result.stderr.strip()}")
            return None
        return json.loads(result.stdout)
    print(f"ERROR: giving up on {xrootd_path} after {retries} attempts")
    return None


def get_lumi_file_map(files):
    def _get_lumi_file_map_one(xrootd_path):
        run_lumis = _read_via_subprocess(_LUMI_READER, xrootd_path)
        if run_lumis is None:
            return xrootd_path, set()
        return xrootd_path, set(tuple(run_lumi) for run_lumi in run_lumis)

    with ThreadPoolExecutor(max_workers=XROOTD_WORKERS) as executor:
        results = list(tqdm(
            executor.map(_get_lumi_file_map_one, files),
            total=len(files), desc="Reading supplement lumis",
        ))

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
    sorted_runs = sorted(runs)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(tqdm(
            executor.map(lambda run: _get_central_run_one(dataset, run), sorted_runs),
            total=len(sorted_runs), desc="Reading central lumis",
        ))
    for files in results:
        for file, run_lumis in files.items():
            index.setdefault(file, []).extend(run_lumis)
    return index


def get_central_files(dataset, retries=3, delay=5):
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            ["dasgoclient", "-query", f"file dataset={dataset}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            break
        print(f"WARNING: dasgoclient query failed for dataset {dataset} (attempt {attempt}/{retries}): {result.stderr.strip()}")
        if attempt < retries:
            time.sleep(delay)
    else:
        print(f"ERROR: dasgoclient query failed for dataset {dataset} after {retries} attempts")
        sys.exit(1)

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_supplement_version(files):
    # Assumes all files in a supplement production share one version -- only
    # the first file is read rather than checking every file for consistency.
    versions = _read_via_subprocess(_VERSION_READER, files[0])
    if not versions:
        print(f"ERROR: could not read version from {files[0]}")
        sys.exit(1)

    if len(versions) != 1:
        print(f"ERROR: {files[0]} has inconsistent versions within itself: {sorted(versions)}")
        sys.exit(1)

    return versions[0]


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


def get_supp_def(dataset, year, sample, era, supplements_path):
    files = eos_helper.get_root_files(supplements_path, recursive=True)

    if not files:
        print("ERROR: not files found")
        exit(1)
    print(f"Found {len(files)} files")

    if all(NUMBERED_SUPPLEMENT_RE.match(os.path.basename(f)) for f in files):
        print("Reading runs/lumis from supplement files...")
        supp_lumis_to_file = get_lumi_file_map(files)
        print(f"Found {len(supp_lumis_to_file)} unique run/lumi pairs")

        print("Reading run/lumis of central files via dasgoclient...")
        runs = {run for run, _ in supp_lumis_to_file}
        central_file_to_lumis = get_central_runs_lumis(dataset, runs)

        print("Matching central files to supplement files...")
        file_mapping = {}
        for central_file, central_lumis in central_file_to_lumis.items():
            # A lumi with no entry has no supplement event, e.g. it failed the
            # trigger filter -- not an error, just skip it.
            supp_files = sorted(set(
                supp_lumis_to_file[l] for l in central_lumis if l in supp_lumis_to_file
            ))
            file_mapping[central_file] = supp_files
    else:
        print("Supplement files are named after central files -- matching by filename...")
        central_files = get_central_files(dataset)
        supp_by_basename = {os.path.basename(f): f for f in files}

        file_mapping = {}
        for central_file in central_files:
            supp_file = supp_by_basename.get(os.path.basename(central_file))
            if supp_file is None:
                print(f"WARNING: no supplement file found for central file {central_file}")
                file_mapping[central_file] = []
            else:
                file_mapping[central_file] = [supp_file]

    print("Reading supplement version...")
    version = get_supplement_version(files)
    print(f"Supplement version: {version}")

    definition = {
        "metadata": {
            "dataset": dataset,
            "sample": sample,
            "year": year,
            "version": version
        },
        "files": file_mapping
    }

    if era is not None:
        definition["metadata"]["era"] = era

    return definition


def main():
    # If the script appears to hang, run `kill -SIGUSR1 <pid>` to dump every
    # thread's current stack to stderr without killing the process.
    faulthandler.register(signal.SIGUSR1, all_threads=True)

    parser = argparse.ArgumentParser(description="Create supplement definition JSON files")

    auto_group = parser.add_argument_group("Automatic Mode")
    auto_group.add_argument(
        "--samples", nargs="+",
        choices=["EGamma", "Muon", "MuonEG", "MET", "Data", "MC", "DY", "Diboson", "TTbar", "SingleTop", "QCDMu", "QCDEle"]
    )
    auto_group.add_argument(
        "--years", nargs="+",
        choices=["2022_preEE", "2022_postEE", "2022", "2023_preBPix", "2023_postBPix", "2023", "2024", "2025"]
    )
    auto_group.add_argument(
        "--eras", nargs="+",
        help="Optional: restrict to specific era(s) within the selected years (e.g. --eras C D). Data samples only."
    )
    auto_group.add_argument("--definition-path", default="datasets/sources/datasets.yaml")
    auto_group.add_argument("--output-dir", default="datasets/supplements", help="Directory to write one JSON file per sample into")

    manual_group = parser.add_argument_group("Manual Mode")
    manual_group.add_argument("--eos-dir", help="Path to an EOS directory that contains the supplement files")
    manual_group.add_argument("--dataset", help="The NanoAOD dataset the supplement files are for")
    manual_group.add_argument("--json-key", help="The target dataset key in the output JSON")
    manual_group.add_argument("--sample", help="The sample name for the supplement definition")
    manual_group.add_argument("--year", help="The year for the supplement definition")
    manual_group.add_argument("--era", help="The era for the supplement definition")
    manual_group.add_argument("--output", default="supplement.json", help="The target output file")

    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument("--overwrite", action="store_true", help="Replace an existing key in the output file")
    write_mode_group.add_argument("--append", action="store_true", help="Merge into an existing key (e.g. add EGamma1 files to EGamma0)")
    args = parser.parse_args()

    auto_args_given = bool(args.samples or args.years)
    manual_args_given = bool(
        args.eos_dir or args.dataset or args.json_key or args.sample or args.year or args.era
    )

    if auto_args_given and manual_args_given:
        parser.error(
            "Cannot mix Automatic Mode args (--samples/--years) with "
            "Manual Mode args (--eos-dir/--dataset/--json-key/--sample/--year/--era)"
        )
    elif auto_args_given:
        if not (args.samples and args.years):
            parser.error("Automatic Mode requires both --samples and --years")
        auto = True
    elif manual_args_given:
        missing = [
            name for name, value in [
                ("--eos-dir", args.eos_dir),
                ("--dataset", args.dataset),
                ("--json-key", args.json_key),
                ("--sample", args.sample),
                ("--year", args.year),
            ] if not value
        ]
        if missing:
            parser.error(f"Manual Mode requires {', '.join(missing)}")
        auto = False
    else:
        parser.error(
            "Must provide either Automatic Mode args (--samples/--years) or "
            "Manual Mode args (--eos-dir/--dataset/--json-key/--sample/--year)"
        )

    if auto:
        catalog = DatasetCatalog(args.definition_path)
        dataset_defs = catalog.get(
            sample=expand_samples(args.samples),
            year=expand_years(args.years),
            era=args.eras,
        )

        os.makedirs(args.output_dir, exist_ok=True)

        existing_keys_cache = {}

        def existing_keys(output):
            if output not in existing_keys_cache:
                if os.path.exists(output):
                    with open(output) as f:
                        existing_keys_cache[output] = set(json.load(f).keys())
                else:
                    existing_keys_cache[output] = set()
            return existing_keys_cache[output]

        seen_keys = set()
        skipped = []
        failures = []
        for d in dataset_defs:
            output = os.path.join(args.output_dir, f"{d.sample}.json")

            already_exists = (
                d.key not in seen_keys
                and not args.overwrite
                and not args.append
                and d.key in existing_keys(output)
            )
            if already_exists:
                print(f"SKIPPING '{d.key}': already exists in {output} (use --overwrite or --append)")
                skipped.append(d.key)
                continue

            overwrite = args.overwrite and d.key not in seen_keys
            append = args.append or d.key in seen_keys

            cmd = [
                sys.executable, __file__,
                "--eos-dir", f"{EOS_REDIRECTOR}/{d.supplements_path}",
                "--dataset", d.nanoaod,
                "--json-key", d.key,
                "--sample", d.sample,
                "--year", d.year,
                "--output", output,
            ]
            if d.era is not None:
                cmd += ["--era", d.era]
            if overwrite:
                cmd.append("--overwrite")
            if append:
                cmd.append("--append")

            proc = subprocess.Popen(cmd)
            print(f"Running '{d.key}' in subprocess (pid {proc.pid})")
            returncode = proc.wait()

            if returncode != 0:
                print(f"SKIPPING '{d.key}': subprocess exited with code {returncode}, see error above")
                failures.append(d.key)
            else:
                seen_keys.add(d.key)

        if skipped:
            print(f"\n{len(skipped)} dataset(s) already existed and were skipped:")
            for key in skipped:
                print(f"  {key}")

        if failures:
            print(f"\n{len(failures)} dataset(s) failed and were skipped:")
            for key in failures:
                print(f"  {key}")
    else:
        supp_def = get_supp_def(
            dataset=args.dataset,
            year=args.year,
            era=args.era,
            sample=args.sample,
            supplements_path=args.eos_dir
        )

        save(args.json_key, supp_def, args.output, args.overwrite, args.append)


if __name__ == "__main__":
    main()
