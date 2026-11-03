import argparse
from catalog import DatasetCatalog
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import multiprocessing as mp
import os
from queue import Empty
import scripts.eos_helper as eos_helper
import subprocess
from rich.progress import Progress, ProgressColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
import uproot

DATA_SAMPLES = ["EGamma", "Muon", "MuonEG", "MET"]
MC_SAMPLES = ["DY", "Diboson", "TTbar", "SingleTop", "QCDMu", "QCDEle", "Signal"]
SAMPLES = DATA_SAMPLES + MC_SAMPLES

YEARS = ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]
ERAS = ["C", "D", "E", "F", "G", "H", "I"]

EOS_REDIRECTOR = "root://cmseos.fnal.gov/"


class StatusColumn(ProgressColumn):
    def __init__(self):
        super().__init__()
        self.spinner = Spinner("dots", style="cyan")

    def render(self, task):
        if not task.fields.get("started"):
            return self.spinner.render(task.get_time())
        dots = Text()
        for status in task.fields.get("step_statuses", []):
            dots.append("* ", style=self._get_style(status))
        return dots

    def _get_style(self, status):
        if status == "pending": return "grey50"
        elif status == "active": return "yellow"
        elif status == "done": return "green"
        else: return "red"


class BarOrDoneColumn(ProgressColumn):
    def __init__(self):
        super().__init__()
        self._bar = BarColumn()
        self._pct = TaskProgressColumn()
        self._mofn = MofNCompleteColumn()

    def render(self, task):
        if task.fields.get("done"):
            return Text("Done", style="bold green")
        if task.fields.get("failed"):
            return Text("Failed", style="bold red")
        if not task.fields.get("started"):
            return Text("")
        if not task.fields.get("show_bar", True):
            return Text("")

        grid = Table.grid(padding=(0, 1))
        grid.add_row(self._bar.render(task), self._pct.render(task), self._mofn.render(task))
        return grid


def get_lumis_from_file(file, lumis_tree_path):
    with uproot.open(f"{file}:{lumis_tree_path}") as tree:
        arrays = tree.arrays(["run", "luminosityBlock"])

    return list(zip(arrays["run"].tolist(), arrays["luminosityBlock"].tolist()))


def load_skim_files(dataset_def, skim_channel, skim_dir="datasets/skims"):
    """Return the skim ROOT files for a dataset from the already-built skim
    dataset definition, or None if that definition doesn't have this
    dataset's key yet."""
    path = f"{skim_dir}/{skim_channel}/{dataset_def.sample}.json"
    if not os.path.exists(path):
        return None

    with open(path) as f:
        data = json.load(f)

    entry = data.get(dataset_def.key)
    return entry["files"] if entry else None


def load_rejected_lumis(dataset_def, supp_dir="datasets/supplements"):
    """Return the rejected lumis from the central supplement definition for
    this dataset, or None if it doesn't have any."""
    path = f"{supp_dir}/{dataset_def.sample}.json"
    if not os.path.exists(path):
        return None

    with open(path) as f:
        data = json.load(f)

    return data.get(dataset_def.key, {}).get("rejected_lumis")


def find_duplicated_lumis(file_to_lumis):
    lumi_to_files = {}
    for file, lumis in file_to_lumis.items():
        for lumi in lumis:
            lumi_to_files.setdefault(tuple(lumi), set()).add(file)

    return sorted([list(lumi) for lumi, files in lumi_to_files.items() if len(files) > 1])


def get_lumis_from_dataset(dataset, run):
    result = subprocess.run(
        # TODO: Can we make this query based on file, not run? MC only has 1 run,
        #       so it takes awhile
        ["dasgoclient", "-query", f"file,lumi dataset={dataset} run={run} status=valid", "-json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print("ERROR: dasgoclient error")
        exit(1)

    file_to_lumi_map = {}
    for record in json.loads(result.stdout):
        file = record["file"][0]["name"]
        lumis = [(run, lumi) for lumi in record["lumi"][0]["number"]]
        file_to_lumi_map[file] = lumis

    return file_to_lumi_map


def read_supplement_version(file):
    with uproot.open(f"{file}:supplementTree/Runs") as tree:
        arrays = tree.arrays(["version"])
    return arrays[0].version


def merge_definitions(existing, new):
    existing_meta = existing["metadata"]
    new_meta = new["metadata"]

    for field in ("sample", "year", "era", "version"):
        if existing_meta.get(field) != new_meta.get(field):
            print(
                f"ERROR: cannot append -- existing '{field}' ({existing_meta.get(field)!r}) "
                f"does not match new '{field}' ({new_meta.get(field)!r})"
            )
            exit(1)

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
            exit(1)

    merged_files = dict(existing["files"])
    merged_files.update(new["files"])

    merged = {"metadata": {**existing_meta, "dataset": existing_datasets}}

    if "rejected_lumis" in existing or "rejected_lumis" in new:
        rejected = {tuple(l) for l in existing.get("rejected_lumis", []) + new.get("rejected_lumis", [])}
        merged["rejected_lumis"] = sorted([list(l) for l in rejected])

    merged["files"] = merged_files
    return merged


def save(key, supp_def, output, overwrite, append):
    if os.path.exists(output):
        with open(output) as f:
            data = json.load(f)
    else:
        data = {}

    if key in data and not overwrite and not append:
        print(f"ERROR: key '{key}' already exists in {output}. Use --overwrite to replace it or --append to merge into it.")
        exit(1)

    if key in data and append:
        supp_def = merge_definitions(data[key], supp_def)

    data[key] = supp_def
    with open(output, "w") as f:
        json.dump(data, f, indent=4)


def read_supplement_lumis(supp_files, report_fn):
    supp_lumis_to_file = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(get_lumis_from_file, supp_file, "supplementTree/Events"): supp_file
            for supp_file in supp_files
        }

        for future in as_completed(futures):
            supp_file = futures[future]
            for run, lumi in future.result():
                supp_lumis_to_file[(run, lumi)] = supp_file

            report_fn(advance=1)

    return supp_lumis_to_file


def read_file_lumis(files, report_fn):
    """Equivalent of read_central_lumis for files that aren't registered in DAS
    (skim output, NanoAOD on EOS): read each file's (run, luminosityBlock)
    directly instead of querying DAS."""
    file_to_lumis = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(get_lumis_from_file, file, "Events"): file
            for file in files
        }

        for future in as_completed(futures):
            file = futures[future]
            lfn = "/store/" + file.split("/store/", 1)[1]
            file_to_lumis[lfn] = future.result()
            report_fn(advance=1)

    return file_to_lumis


def check_unique_lumis(file_to_lumis):
    lumi_to_file = {}
    for file, lumis in file_to_lumis.items():
        for lumi in lumis:
            if lumi in lumi_to_file and lumi_to_file[lumi] != file:
                raise ValueError(f"run/lumi {lumi} is in both {lumi_to_file[lumi]} and {file}")
            lumi_to_file[lumi] = file


def read_central_lumis(dataset, runs, report_fn):
    central_file_to_lumis = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(get_lumis_from_dataset, dataset, run): run
            for run in runs
        }

        for future in as_completed(futures):
            run = futures[future]
            for file, lumis in future.result().items():
                central_file_to_lumis.setdefault(file, []).extend(lumis)

            report_fn(advance=1)

    return central_file_to_lumis


def resolve_supp_files(dataset_def):
    """Return the supplement ROOT files for a dataset, or None if nothing
    is available to process yet."""
    return eos_helper.try_get_root_files(f"{EOS_REDIRECTOR}{dataset_def.supplements_path}")


def get_supplement_definition(dataset_def, central_file_to_lumis, supp_lumis_to_file, version, rejected_lumis=None):
    central_to_supp_mapping = {}
    for central_file, central_lumis in central_file_to_lumis.items():
        supp_files = list(set(supp_lumis_to_file[l] for l in central_lumis if l in supp_lumis_to_file))
        central_to_supp_mapping[central_file] = supp_files

    supp_def = {
        "metadata": {
            "dataset": dataset_def.nanoaod,
            "sample": dataset_def.sample,
            "year": dataset_def.year,
            "version": version
        },
    }

    if dataset_def.era is not None:
        supp_def["metadata"]["era"] = dataset_def.era

    if rejected_lumis is not None:
        supp_def["rejected_lumis"] = rejected_lumis

    supp_def["files"] = central_to_supp_mapping

    return supp_def


def process_dataset(dataset_def, supp_files, skim_channel, skim_files, rejected_lumis, message_queue):
    step_statuses = ["pending", "pending", "pending", "pending"]

    def report(advance=0, reset=False, total=None, description=None, **fields):
        message_queue.put((dataset_def.key, reset, total, description, advance, fields))

    def set_step(index, status, **fields):
        step_statuses[index] = status
        report(step_statuses=list(step_statuses), **fields)

    report(started=True)

    set_step(0, "active", show_bar=True)
    report(reset=True, total=len(supp_files), description="Reading supplement files")
    supp_lumis_to_file = read_supplement_lumis(supp_files, report)
    set_step(0, "done")

    set_step(1, "active", show_bar=True)
    if skim_channel:
        report(reset=True, total=len(skim_files), description="Reading skim files")
        central_file_to_lumis = read_file_lumis(skim_files, report)
    elif dataset_def.type == "eos":
        eos_files = eos_helper.get_root_files(f"{EOS_REDIRECTOR}{dataset_def.nanoaod}")
        report(reset=True, total=len(eos_files), description="Reading NanoAOD files")
        central_file_to_lumis = read_file_lumis(eos_files, report)
        check_unique_lumis(central_file_to_lumis)
    else:
        runs = {run for run, _ in supp_lumis_to_file}
        report(reset=True, total=len(runs), description="Reading central files")
        central_file_to_lumis = read_central_lumis(dataset_def.nanoaod, runs, report)

        if dataset_def.is_mc:
            report(reset=True, total=len(runs), description="Reading MiniAOD files")
            miniaod_file_to_lumis = read_central_lumis(dataset_def.miniaod, runs, report)
            rejected_lumis = find_duplicated_lumis(miniaod_file_to_lumis)
    set_step(1, "done")

    set_step(2, "active", show_bar=False)
    version = read_supplement_version(supp_files[0])
    supp_def = get_supplement_definition(
        dataset_def, central_file_to_lumis, supp_lumis_to_file, version, rejected_lumis
    )
    set_step(2, "done")

    return dataset_def.key, supp_def


def cleanup_finished_tasks(pending, output_dir, overwrite, append, progress, tasks, step_statuses_by_key):
    for key in [k for k, result in pending.items() if result.ready()]:
        result = pending.pop(key)
        try:
            _, supp_def = result.get()
            sample = supp_def["metadata"]["sample"]
            output = f"{output_dir}/{sample}.json"

            step_statuses = step_statuses_by_key[key]
            step_statuses[3] = "active"
            progress.update(tasks[key], step_statuses=list(step_statuses), show_bar=False)

            save(key, supp_def, output, overwrite, append)
            if "rejected_lumis" in supp_def:
                progress.console.print(f"{key}: {len(supp_def['rejected_lumis'])} rejected lumis")

            step_statuses[3] = "done"
            progress.update(tasks[key], step_statuses=list(step_statuses), done=True)
        except Exception as e:
            print(f"ERROR: '{key}' failed: {e}")
            progress.update(tasks[key], failed=True)


def has_supplement_definition(dataset_def, output_dir):
    output = f"{output_dir}/{dataset_def.sample}.json"
    if not os.path.exists(output):
        return False

    with open(output) as f:
        data = json.load(f)

    return dataset_def.key in data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", nargs="+", choices=SAMPLES)
    parser.add_argument("--years", nargs="+", choices=YEARS)
    parser.add_argument("--eras", nargs="+", choices=ERAS)
    parser.add_argument("--definition-path", default="datasets/sources/datasets.yaml")
    parser.add_argument("--output-dir", default=None, help="Defaults to datasets/supplements, or datasets/skim_supplements when --skim-channel is set")
    parser.add_argument(
        "--skim-channel", default=None,
        help="Match supplement files against a channel's skim output instead of central "
             "NanoAOD -- reads the skim file list from datasets/skims/<channel>/<sample>.json "
             "and opens each skim file directly (skim files aren't registered in DAS, so "
             "there's no dataset to query). Output goes to datasets/skim_supplements/<channel>/."
    )
    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument("--overwrite", action="store_true", help="Replace an existing key in the output file")
    write_mode_group.add_argument("--append", action="store_true", help="Merge into an existing key (e.g. add EGamma1 files to EGamma0)")
    args = parser.parse_args()

    output_dir = args.output_dir or ("datasets/skim_supplements" if args.skim_channel else "datasets/supplements")
    if args.skim_channel:
        output_dir = f"{output_dir}/{args.skim_channel}"

    catalog = DatasetCatalog(args.definition_path)

    dataset_defs = catalog.get(sample=args.samples, year=args.years, era=args.eras)

    dataset_defs = [
        d for d in dataset_defs
        if not has_supplement_definition(d, output_dir) or args.overwrite or args.append
    ]

    resolved = {}
    not_ready_no_supplements = []
    not_ready_no_skim = []
    for d in dataset_defs:
        supp_files = resolve_supp_files(d)
        if supp_files is None:
            not_ready_no_supplements.append(d.key)
            continue

        skim_files = None
        rejected_lumis = None
        if args.skim_channel:
            skim_files = load_skim_files(d, args.skim_channel)
            if skim_files is None:
                not_ready_no_skim.append(d.key)
                continue
            rejected_lumis = load_rejected_lumis(d)

        resolved[d.key] = (supp_files, skim_files, rejected_lumis)

    if not_ready_no_supplements:
        print(f"Skipping {len(not_ready_no_supplements)} dataset(s) with no supplement output yet: {', '.join(not_ready_no_supplements)}")
    if not_ready_no_skim:
        print(f"Skipping {len(not_ready_no_skim)} dataset(s) with no skim dataset definition yet: {', '.join(not_ready_no_skim)}")

    can_process = list(resolved.keys())
    if len(can_process) > 0:
        os.makedirs(output_dir, exist_ok=True)

    with Progress(
        TextColumn("[bold]{task.fields[dataset]:<30}"),
        StatusColumn(),
        BarOrDoneColumn()
    ) as progress, mp.Manager() as manager:
        message_queue = manager.Queue()
        tasks = {
            d.key: progress.add_task(
                "", total=100, dataset=d.key,
                started=False, done=False, failed=False, show_bar=True,
                step_statuses=["pending", "pending", "pending", "pending"],
            )
            for d in dataset_defs
        }
        step_statuses_by_key = {d.key: ["pending", "pending", "pending", "pending"] for d in dataset_defs}

        def apply_message(key, reset, total, desc, advance, fields):
            task_id = tasks[key]
            if reset:
                progress.reset(task_id, total=total, description=desc)
            if advance:
                progress.update(task_id, advance=advance)
            if fields:
                progress.update(task_id, **fields)
                if "step_statuses" in fields:
                    step_statuses_by_key[key] = fields["step_statuses"]

        with mp.Pool(processes=1, maxtasksperchild=1) as pool:
            pending = {
                d.key: pool.apply_async(
                    process_dataset,
                    args=(d, resolved[d.key][0], args.skim_channel, resolved[d.key][1], resolved[d.key][2], message_queue)
                )
                for d in dataset_defs if d.key in can_process
            }

            try:
                while pending:
                    cleanup_finished_tasks(
                        pending, output_dir, args.overwrite, args.append,
                        progress, tasks, step_statuses_by_key,
                    )

                    try:
                        apply_message(*message_queue.get(timeout=0.1))
                    except Empty:
                        continue

                while not message_queue.empty():
                    apply_message(*message_queue.get_nowait())

            except KeyboardInterrupt:
                pool.terminate()
                pool.join()
                raise


if __name__ == "__main__":
    main()
