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
MC_SAMPLES = ["DY", "Diboson", "TTbar", "SingleTop", "QCDMu", "QCDEle"]
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


def get_lumis_from_dataset(dataset, run):
    result = subprocess.run(
        # TODO: Can we make this query based on file, not run? MC only has 1 run,
        #       so it takes awhile
        ["dasgoclient", "-query", f"file,lumi dataset={dataset} run={run}", "-json"],
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

    return {
        "metadata": {**existing_meta, "dataset": existing_datasets},
        "files": merged_files,
    }


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


def get_supplement_definition(dataset_def, central_file_to_lumis, supp_lumis_to_file, version):
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
        "files": central_to_supp_mapping
    }

    if dataset_def.era is not None:
        supp_def["metadata"]["era"] = dataset_def.era

    return supp_def


def process_dataset(dataset_def, message_queue):
    step_statuses = ["pending", "pending", "pending", "pending"]

    def report(advance=0, reset=False, total=None, description=None, **fields):
        message_queue.put((dataset_def.key, reset, total, description, advance, fields))

    def set_step(index, status, **fields):
        step_statuses[index] = status
        report(step_statuses=list(step_statuses), **fields)

    report(started=True)

    supp_files = eos_helper.get_root_files(f"{EOS_REDIRECTOR}/{dataset_def.supplements_path}") # TODO: make eos helper throw exception if this fails

    set_step(0, "active", show_bar=True)
    report(reset=True, total=len(supp_files), description="Reading supplement files")
    supp_lumis_to_file = read_supplement_lumis(supp_files, report)
    set_step(0, "done")

    set_step(1, "active", show_bar=True)
    runs = {run for run, _ in supp_lumis_to_file}
    report(reset=True, total=len(runs), description="Reading central files")
    central_file_to_lumis = read_central_lumis(dataset_def.nanoaod, runs, report)
    set_step(1, "done")

    set_step(2, "active", show_bar=False)
    version = read_supplement_version(supp_files[0])
    supp_def = get_supplement_definition(dataset_def, central_file_to_lumis, supp_lumis_to_file, version)
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
    parser.add_argument("--output-dir", default="datasets/supplements")
    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument("--overwrite", action="store_true", help="Replace an existing key in the output file")
    write_mode_group.add_argument("--append", action="store_true", help="Merge into an existing key (e.g. add EGamma1 files to EGamma0)")
    args = parser.parse_args()

    catalog = DatasetCatalog(args.definition_path)

    dataset_defs = catalog.get(sample=args.samples, year=args.years, era=args.eras)

    can_process = [
        d.key for d in dataset_defs
        if not has_supplement_definition(d, args.output_dir) or args.overwrite or args.append
    ]
    if len(can_process) > 0:
        os.makedirs(args.output_dir, exist_ok=True)

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

        with mp.Pool(processes=3, maxtasksperchild=1) as pool:
            pending = {
                d.key: pool.apply_async(process_dataset, args=(d, message_queue))
                for d in dataset_defs if d.key in can_process
            }

            try:
                while pending:
                    cleanup_finished_tasks(
                        pending, args.output_dir, args.overwrite, args.append,
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
