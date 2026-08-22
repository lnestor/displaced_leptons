import os, getpass
import sys
import argparse
import cloudpickle
import csv
import hashlib
import socket
import logging
import traceback
import yaml
from yaml import Loader, Dumper
import click
import time
from rich import print as rprint
from rich.table import Table
from rich.console import Console

from coffea.util import save
from coffea import processor

from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.utils.utils import load_config, path_import, adapt_chunksize, save_failed_jobs, load_failed_jobs, FAILED_JOBS_FILENAME
from pocket_coffea.utils.logging import setup_logging
from pocket_coffea.utils.time import wait_until
from pocket_coffea.parameters import defaults as parameters_utils
from pocket_coffea.executors import executors_base, executors_manual_jobs
from pocket_coffea.utils.benchmarking import print_processing_stats

from lib.workflow.runner import Runner as DisplacedLeptonsRunner

FAILED_FILES_CSV = "failed_files.csv"


def save_failed_files(dataset, failed_files, outputdir):
    """Replace failed_files.csv's rows for `dataset` with whatever failed in
    this run (may be empty, correctly clearing entries that succeeded this
    time). Also writes/overwrites file_errors/<hash>.txt for each currently
    failing file. Called once per dataset, immediately after that dataset's
    run completes -- unlike failed_jobs.json, this can't wait until the
    whole script finishes, both so it survives an early interruption and so
    a later --resubmit-failed sees an accurate picture.

    Only files actually attempted this run can be spoken to -- a
    files-only resubmission (see --resubmit-failed) only reprocesses the
    previously-failed subset, so replacing this dataset's rows wholesale is
    still correct: whatever isn't in `failed_files` this time must have
    just succeeded.
    """
    csv_path = os.path.join(outputdir, FAILED_FILES_CSV)
    errors_dir = os.path.join(outputdir, "file_errors")
    os.makedirs(errors_dir, exist_ok=True)

    existing_rows = set()
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            existing_rows = {(row["dataset"], row["filename"]) for row in csv.DictReader(f)}

    previous_rows_for_dataset = {row for row in existing_rows if row[0] == dataset}
    existing_rows -= previous_rows_for_dataset

    new_rows_for_dataset = set()
    for _, filename, error in failed_files:
        new_rows_for_dataset.add((dataset, filename))
        error_id = hashlib.md5(f"{dataset}|{filename}".encode()).hexdigest()
        with open(os.path.join(errors_dir, f"{error_id}.txt"), "w") as f:
            f.write(f"dataset: {dataset}\nfilename: {filename}\n\n{error}\n")

    # Files that were failing before but aren't anymore -- delete their
    # error text so it doesn't outlive the failure it describes.
    for resolved_dataset, resolved_filename in previous_rows_for_dataset - new_rows_for_dataset:
        error_id = hashlib.md5(f"{resolved_dataset}|{resolved_filename}".encode()).hexdigest()
        error_path = os.path.join(errors_dir, f"{error_id}.txt")
        if os.path.exists(error_path):
            os.remove(error_path)

    existing_rows |= new_rows_for_dataset

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dataset", "filename"])
        writer.writerows(sorted(existing_rows))


def update_failed_jobs(dataset, succeeded, outputdir):
    """Replace failed_jobs.json's entry for `dataset` based on this run's
    outcome -- removed if it succeeded, added if it failed. Called
    immediately per dataset rather than batched to the end of the script,
    for the same reasons as save_failed_files: survives an early
    interruption, and keeps --resubmit-failed accurate without needing a
    full pass to complete. Merges against what's on disk rather than
    overwriting wholesale, since a run restricted by --filter-datasets (or
    similar) may not touch every dataset a previous failed_jobs.json knows
    about.
    """
    failed_jobs = set(load_failed_jobs(outputdir) or [])
    if succeeded:
        failed_jobs.discard(dataset)
    else:
        failed_jobs.add(dataset)
    save_failed_jobs(sorted(failed_jobs), outputdir)


def load_failed_files(outputdir):
    """Read failed_files.csv into {dataset: [filename, ...]}, or {} if absent."""
    csv_path = os.path.join(outputdir, FAILED_FILES_CSV)
    failed_files_by_dataset = {}
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                failed_files_by_dataset.setdefault(row["dataset"], []).append(row["filename"])
    return failed_files_by_dataset


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option('--cfg', required=True, type=str,
              help='Config file with parameters specific to the current run')
@click.option("-ro", "--custom-run-options", type=str, default=None, help="User provided run options .yaml file")
@click.option("-o", "--outputdir", required=True, type=str, help="Output folder")
@click.option("-t", "--test", is_flag=True, help="Run with limit 1 interactively")
@click.option("-lf","--limit-files", type=int, help="Limit number of files")
@click.option("-lc","--limit-chunks", type=int, help="Limit number of chunks", default=None)
@click.option("-s","--scaleout", type=int, help="Overwrite scaleout config" )
@click.option("-c","--chunksize", type=int, help="Overwrite chunksize config" )
@click.option("-q","--queue", type=str, help="Overwrite queue config" )
@click.option("--filter-years", type=str, help="Filter the data taking period of the datasets to be processed (comma separated list)")
@click.option("--filter-samples", type=str, help="Filter the samples to be processed (comma separated list)")
@click.option("--filter-datasets", type=str, help="Filter the datasets to be processed (comma separated list)")
@click.option("--resubmit-failed", is_flag=True, help="Resubmit only failed datasets and previously-skipped files from the previous run (from failed_jobs.json and/or failed_files.csv)", default=False)

def run(cfg,  custom_run_options, outputdir, test, limit_files,
           limit_chunks, scaleout, chunksize,
           queue,
           filter_years, filter_samples, filter_datasets, resubmit_failed):
    '''Run an analysis on NanoAOD files using PocketCoffea processors'''
    # Setting up the output dir
    os.makedirs(outputdir, exist_ok=True)
    outfile = os.path.join(
        outputdir, "output_{}.coffea"
    )
    logfile = os.path.join(outputdir, "logfile.log")

    # Prepare logging
    if (not setup_logging(console_log_output="stdout", console_log_level="INFO", console_log_color=True,
                        logfile_file=logfile, logfile_log_level="info", logfile_log_color=False,
                        log_line_template="%(color_on)s[%(levelname)-8s] %(message)s%(color_off)s")):
        print("Failed to setup logging, aborting.")
        exit(1)

    rprint("[bold]Loading the configuration file...[/]")
    if cfg[-3:] == ".py":
        # Load the script
        config = load_config(cfg, save_config=True, outputdir=outputdir)
    elif cfg[-4:] == ".pkl":
        config = cloudpickle.load(open(cfg,"rb"))
        if not config.loaded:
            config.load()
        config.save_config(outputdir)
        rprint("[italic]The configuration file is saved at {outputdir} [/]")
    else:
        raise sys.exit("Please provide a .py/.pkl configuration file")

    print(config)

    # This script only supports the LPC dask executor -- enforced by not
    # exposing an --executor option at all.
    executor_name = "dask"
    site = "lpc"

    # Getting the default run_options
    run_options_defaults = parameters_utils.get_default_run_options()
    run_options = run_options_defaults["general"]
    # If there are default specific default run_options load them
    if site in run_options_defaults:
        run_options.update(run_options_defaults[site])
    if executor_name in run_options_defaults:
        run_options.update(run_options_defaults[executor_name])
    if f"{executor_name}@{site}" in run_options_defaults:
        run_options.update(run_options_defaults[f"{executor_name}@{site}"])
    # Now merge on top the user defined run_options
    if custom_run_options:
        run_options = parameters_utils.merge_parameters_from_files(run_options, custom_run_options)

    if limit_files!=None:
        run_options["limit-files"] = limit_files
        config.filter_dataset(run_options["limit-files"])

    if limit_chunks!=None:
        run_options["limit-chunks"] = limit_chunks

    if scaleout!=None:
        run_options["scaleout"] = scaleout

    if chunksize!=None:
        run_options["chunksize"] = chunksize

    if queue!=None:
        run_options["queue"] = queue

    # TODO: check if we need to set these or if they have a good default?
    # Option I never use
    run_options["blocklist-sites"] = False
    run_options["use-redirector"] = False
    run_options["recreate-queue"] = False

    # Options I always want
    run_options["skip-bad-files"] = True


    #Parsing additional runoptions from command line in the format --option=value, or --option.
    ctx = click.get_current_context()
    for arg in ctx.args:
        if arg.startswith("--"):
            if "=" in arg:
                key, value = arg.split("=")
                run_options[key[2:]] = value
            else:
                next_arg = ctx.args[ctx.args.index(arg)+1] if ctx.args.index(arg)+1 < len(ctx.args) else None
                if next_arg and not next_arg.startswith("--"):
                    run_options[arg[2:]] = next_arg
                else:
                    run_options[arg[2:]] = True


    ## Default config for testing: limit to 2 files and 2 chunks
    if test:
        run_options["limit-files"] = limit_files if limit_files else 2
        run_options["limit-chunks"] = limit_chunks if limit_chunks else 2
        config.filter_dataset(run_options["limit-files"])

    # Run option display
    table = Table(title="Run Configuration")
    table.add_column("Option", style="cyan")
    table.add_column("Value", style="white")

    for key, value in sorted(run_options.items()):
        table.add_row(key, str(value))

    Console().print(table)

    from lib.workflow import executors_lpc as executors_lib

    logging.getLogger().handlers[0].setLevel("ERROR")

    # Load the executor class from the lib and instantiate it
    executor_factory = executors_lib.get_executor_factory(executor_name, run_options=run_options, outputdir=outputdir)
    # Check the type of the executor_factory
    if not (isinstance(executor_factory, executors_base.ExecutorFactoryABC) or
            isinstance(executor_factory, executors_manual_jobs.ExecutorFactoryManualABC)):
        print("The user defined executor factory lib is not of type ExecutorFactoryABC or ExecutorFactoryManualABC!", executor_name, site)
        exit(1)

    # Filter on the fly the fileset to process by datataking period
    filesets_to_run = config.filesets
    filter_years = filter_years.split(",") if filter_years else None
    filter_samples = filter_samples.split(",") if filter_samples else None
    filter_datasets = filter_datasets.split(",") if filter_datasets else None
    if filter_years:
        filesets_to_run = {dataset: files for dataset, files in filesets_to_run.items() if files["metadata"]["year"] in filter_years}
    if filter_samples:
        filesets_to_run = {dataset: files for dataset, files in filesets_to_run.items() if files["metadata"]["sample"] in filter_samples}
    if filter_datasets:
        filesets_to_run = {dataset: files for dataset, files in filesets_to_run.items() if dataset in filter_datasets}

    # Handle resubmission of failed jobs/files
    failed_files_by_dataset = {}
    if resubmit_failed:
        failed_jobs_to_resubmit = load_failed_jobs(outputdir) or []
        failed_files_by_dataset = load_failed_files(outputdir)

        if len(failed_jobs_to_resubmit) == 0 and len(failed_files_by_dataset) == 0:
            logging.info("No failed jobs or failed files to resubmit.")
            exit(0)

        logging.info(f"Resubmitting {len(failed_jobs_to_resubmit)} fully failed dataset(s): {failed_jobs_to_resubmit}")
        n_failed_files = sum(len(v) for v in failed_files_by_dataset.values())
        logging.info(f"Resubmitting {n_failed_files} failed file(s) across {len(failed_files_by_dataset)} dataset(s): {list(failed_files_by_dataset.keys())}")
        # Note: we will filter/build filesets_groups later after groups are constructed
        # since failed jobs refer to group names, not individual dataset names

    if len(filesets_to_run) == 0:
        print("No datasets to process, closing")
        exit(1)

    # Instantiate the executor

    # Checking if the executor handles the submission or returns a coffea executor
    if executor_factory.handles_submission:
        # in this case we just send to the executor the config file
        executor = executor_factory.submit(config, filesets_to_run, outputdir)
        exit(0)
    else:
        executor = executor_factory.get()

    start_time = time.time()
    filesets_groups = {dataset:{dataset:files} for dataset, files in filesets_to_run.items()}

    # Filter/restrict filesets_groups if resubmitting failed jobs/files
    if resubmit_failed:
        new_groups = {}
        for group_name, fileset_ in filesets_groups.items():
            if group_name in failed_jobs_to_resubmit:
                # Fully failed dataset -- resubmit the whole thing.
                new_groups[group_name] = fileset_
            elif group_name in failed_files_by_dataset:
                # Dataset succeeded overall but some files were skipped --
                # resubmit just those files.
                original = fileset_[group_name]
                new_groups[group_name] = {group_name: {
                    "files": failed_files_by_dataset[group_name],
                    "metadata": original["metadata"],
                }}
        filesets_groups = new_groups
        logging.info(f"Filtered to {len(filesets_groups)} groups/datasets for resubmission")
        if len(filesets_groups) == 0:
            logging.info("No matching failed jobs or files to resubmit.")
            exit(0)

    # Running separately on each dataset
    for group_name, fileset_ in filesets_groups.items():
        dataset_start_time = time.time()
        datasets = list(fileset_.keys())
        if len(datasets) == 1:
            dataset = datasets[0]
            print(f"Working on dataset: {group_name}")
            logging.info(f"Working on dataset: {group_name}")
        else:
            print(f"Working on group of datasets: {group_name} ({len(datasets)} datasets)")
            logging.info(f"Working on group of datasets: {group_name} ({len(datasets)} datasets)")

        n_events_tot = sum([int(files["metadata"]["nevents"]) for files in fileset_.values()])
        if resubmit_failed and group_name in failed_files_by_dataset:
            logging.info(
                "Total number of events: %d (inaccurate -- this count is from the full "
                "dataset, but this run only reprocesses %d previously-failed file(s))",
                n_events_tot, len(failed_files_by_dataset[group_name])
            )
        else:
            logging.info("Total number of events: %d", n_events_tot)

        adapted_chunksize = adapt_chunksize(n_events_tot, run_options)
        if adapted_chunksize != run_options["chunksize"]:
            logging.info(f"Reducing chunksize from {run_options['chunksize']} to {adapted_chunksize} for dataset(s) {group_name}")

        coffea_runner = DisplacedLeptonsRunner(
            executor=executor,
            chunksize=run_options["chunksize"],
            maxchunks=run_options["limit-chunks"],
            skipbadfiles=run_options['skip-bad-files'],
            schema=processor.NanoAODSchema,
            format="root",
        )

        error_log_file = f"{outputdir}/error/run_{group_name}.err"
        try:
            output = coffea_runner(fileset_, treename="Events",
                                   processor_instance=config.processor_instance)
        except Exception:
            error_trace = traceback.format_exc()
            os.makedirs(os.path.dirname(error_log_file), exist_ok=True)
            with open(error_log_file, "w") as f:
                f.write(error_trace)
            logging.error(f"Error occurred, traceback saved to: {os.path.abspath(error_log_file)}")
            output = None

        if output is None:
            logging.error(f"Processing of dataset {group_name} failed, moving to the next one")
            update_failed_jobs(group_name, succeeded=False, outputdir=outputdir)
            continue
        else:
            if os.path.exists(error_log_file):
                os.remove(error_log_file)
            update_failed_jobs(group_name, succeeded=True, outputdir=outputdir)
            save_failed_files(group_name, coffea_runner.failed_files, outputdir)
            if coffea_runner.failed_files:
                logging.warning(f"{len(coffea_runner.failed_files)} file(s) skipped in dataset {group_name}, see {FAILED_FILES_CSV}")

            print(f"Saving output to {outfile.format(group_name)}")
            save(output, outfile.format(group_name))
            print_processing_stats(output, dataset_start_time, run_options["scaleout"])


    remaining_failed = load_failed_jobs(outputdir) or []
    if len(remaining_failed) > 0:
        logging.warning(f"{len(remaining_failed)} job(s) failed. See {os.path.join(outputdir, FAILED_JOBS_FILENAME)}")
    else:
        logging.info("All jobs completed successfully.")


    # If the processor has skimmed NanoAOD, we export a dataset_definition file
    if config.save_skimmed_files and config.do_postprocessing:
        from pocket_coffea.utils.skim import save_skimed_dataset_definition
        save_skimed_dataset_definition(output, f"{outputdir}/skimmed_dataset_definition.json", check_initial_events=not test)

    # Closing the executor if needed
    executor_factory.close()



if __name__ == "__main__":
    run()
