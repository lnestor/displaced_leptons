import argparse
import glob
import os

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from coffea.util import load


def get_args():
    parser = argparse.ArgumentParser(description="Merge per-chunk column parquet files into one file per sample")
    parser.add_argument("-i", "--input-dir", required=True, help="Directory holding one subdirectory of parquet chunks per dataset")
    parser.add_argument("-c", "--coffea-dir", required=True, help="Job output directory holding output_<dataset>.coffea")
    parser.add_argument("-o", "--output-dir", required=True)
    parser.add_argument("--category", default="baseline")
    parser.add_argument("--variation", default="nominal")
    return parser.parse_args()


def read_chunks(path):
    tables = []
    for fname in sorted(glob.glob(f"{path}/*.parquet")):
        table = pq.read_table(fname)
        if table.num_rows > 0:
            tables.append(table)
    return pa.concat_tables(tables) if tables else None


def main():
    args = get_args()
    os.makedirs(args.output_dir, exist_ok=True)

    by_sample = {}
    for dataset_dir in sorted(glob.glob(f"{args.input_dir}/*")):
        dataset = os.path.basename(dataset_dir)
        out = load(f"{args.coffea_dir}/output_{dataset}.coffea")
        sum_genweights = out["sum_genweights"][dataset]
        sample = out["datasets_metadata"]["by_dataset"][dataset]["sample"]

        leaf = f"{args.category}/{args.variation}"
        if os.path.isdir(f"{dataset_dir}/{leaf}"):
            parts = {sample: f"{dataset_dir}/{leaf}"}
        else:
            parts = {
                f"{sample}__{os.path.basename(sub)}": f"{sub}/{leaf}"
                for sub in sorted(glob.glob(f"{dataset_dir}/*"))
            }

        for key, path in parts.items():
            table = read_chunks(path)
            if table is None:
                continue

            weight = table["weight"].to_numpy() / sum_genweights
            table = table.append_column("weight_norm", pa.array(weight))
            expected = out["sumw"][args.category][dataset][key]["nominal"]
            print(f"{key:12s} {dataset[:50]:50s} n={table.num_rows:8d} sumw={weight.sum():12.2f} coffea={expected:12.2f}")
            if not np.isclose(weight.sum(), expected, rtol=1e-6):
                raise ValueError(f"Column weights for {dataset} ({key}) do not match the coffea sumw")
            by_sample.setdefault(key, []).append(table)

    for key, tables in by_sample.items():
        pq.write_table(pa.concat_tables(tables), f"{args.output_dir}/{key}.parquet")
        print(f"Wrote {args.output_dir}/{key}.parquet")


if __name__ == "__main__":
    main()
