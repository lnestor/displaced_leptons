#!/usr/bin/env python3
"""
Build PocketCoffea dataset JSONs always using the FNAL XRootD redirector.
"""
import json
import argparse
from multiprocessing import Pool
from functools import partial

from pocket_coffea.utils.dataset import do_dataset

FNAL_REDIRECTOR = "root://cmsxrootd.fnal.gov//"


def build_datasets(cfg, keys=None, overwrite=False, parallelize=4):
    config = json.load(open(cfg))
    if not keys:
        keys = list(config.keys())

    args = {
        "config": config,
        "local_prefix": None,
        "allowlist_sites": [],
        "include_redirector": False,
        "blocklist_sites": [],
        "prioritylist_sites": [],
        "regex_sites": None,
        "sort_replicas": "geoip",
    }

    if parallelize == 1:
        datasets = [do_dataset(key, **args) for key in keys]
    else:
        with Pool(parallelize) as pool:
            datasets = pool.map(partial(do_dataset, **args), keys)

    for dataset in datasets:
        sample_dict = {}
        for sample in dataset.samples_obj:
            sample_dict.update(
                sample.get_sample_dict(redirector=True, prefix=FNAL_REDIRECTOR)
            )
        dataset._write_dataset(
            dataset.outfile, sample_dict, append=True, overwrite=overwrite
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build PocketCoffea dataset JSONs using the FNAL XRootD redirector. "
            "Outputs a single file per dataset (no _redirector.json variant)."
        )
    )
    parser.add_argument("--cfg", required=True, help="Source dataset definition JSON")
    parser.add_argument("-k", "--keys", nargs="*", metavar="KEY",
                        help="Dataset keys to build (default: all)")
    parser.add_argument("-o", "--overwrite", action="store_true",
                        help="Overwrite existing entries in the output JSON")
    parser.add_argument("-p", "--parallelize", type=int, default=4)
    args = parser.parse_args()

    build_datasets(
        cfg=args.cfg,
        keys=args.keys,
        overwrite=args.overwrite,
        parallelize=args.parallelize,
    )


if __name__ == "__main__":
    main()
