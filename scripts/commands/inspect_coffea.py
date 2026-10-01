import argparse
import json

import hist
from scripts.coffea_file import CoffeaFile


def build_summary(f):
    hist_names = f.hist_names()
    ref_hist = hist_names[0]

    def tree(hist_name):
        return {s: f.get_datasets(hist_name, s) for s in f.get_samples(hist_name)}

    ref_tree = tree(ref_hist)
    samples = {}
    for sample, datasets in ref_tree.items():
        samples[sample] = {
            "type": "data" if f.is_data(sample, ref_hist) else "MC",
            "years": sorted(f.get_years(ref_hist, sample)),
            "datasets": datasets,
        }

    differing = [h for h in hist_names if tree(h) != ref_tree]

    return {
        "file": f.filename,
        "reference_hist": ref_hist,
        "histograms": hist_names,
        "categories": sorted(f.get_categories()),
        "samples": samples,
        "histograms_differing_from_reference": differing,
    }


def build_hist_detail(f, hist_name):
    detail = {}
    for sample in f.get_samples(hist_name):
        detail[sample] = {}
        for dataset in f.get_datasets(hist_name, sample):
            axes = f.get_axes(hist_name, sample, dataset)
            detail[sample][dataset] = {
                "year": f._dataset_year(dataset),
                "axes": [
                    {
                        "name": ax.name,
                        "type": type(ax).__name__,
                        "n_bins": len(ax),
                        "labels": list(ax) if isinstance(ax, hist.axis.StrCategory) else None,
                    }
                    for ax in axes
                ],
            }
    return detail


def print_summary(summary, show_datasets):
    samples = summary["samples"]
    all_years = sorted({y for s in samples.values() for y in s["years"]})

    print(f"File: {summary['file']}")
    print(
        f"Histograms: {len(summary['histograms'])}   Samples: {len(samples)}   "
        f"Categories: {len(summary['categories'])}   Years: {', '.join(all_years)}"
    )

    print("\nSamples")
    name_w = max(len("sample"), *(len(s) for s in samples))
    years_w = max(len("years"), *(len(", ".join(s["years"])) for s in samples.values()))
    print(f"  {'sample':<{name_w}}  {'type':<4}  {'years':<{years_w}}  datasets")
    for sample, info in samples.items():
        print(
            f"  {sample:<{name_w}}  {info['type']:<4}  "
            f"{', '.join(info['years']):<{years_w}}  {len(info['datasets'])}"
        )
        if show_datasets:
            for dataset in info["datasets"]:
                print(f"  {'':<{name_w}}    {dataset}")

    print("\nCategories")
    print("  " + ", ".join(summary["categories"]))

    print("\nHistograms")
    for name in summary["histograms"]:
        print(f"  {name}")

    differing = summary["histograms_differing_from_reference"]
    if differing:
        print(
            f"\nDiffers from '{summary['reference_hist']}' in samples/datasets "
            f"(samples table above is for '{summary['reference_hist']}'):"
        )
        for name in differing:
            print(f"  {name}")


def print_hist_detail(hist_name, detail):
    print(f"\nHistogram '{hist_name}'")
    for sample, datasets in detail.items():
        print(f"  {sample}")
        for dataset, info in datasets.items():
            print(f"    {dataset}  ({info['year']})")

    first = next(iter(next(iter(detail.values())).values()))
    print("  Axes (first dataset)")
    for ax in first["axes"]:
        desc = f"{ax['name']} [{ax['type']}, {ax['n_bins']} bins]"
        if ax["labels"] is not None:
            desc += ": " + ", ".join(ax["labels"])
        print(f"    {desc}")


def main():
    parser = argparse.ArgumentParser(description="Print the samples, years, categories and histograms in a coffea file")
    parser.add_argument("input", help="Coffea file")
    parser.add_argument("--hist", help="Also print the sample/dataset/year tree and axes for this histogram")
    parser.add_argument("--datasets", action="store_true", help="List the dataset keys under each sample")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args()

    f = CoffeaFile(args.input)
    summary = build_summary(f)

    detail = None
    if args.hist is not None:
        if args.hist not in summary["histograms"]:
            parser.error(f"histogram '{args.hist}' not in file. Run without --hist to list them")
        detail = build_hist_detail(f, args.hist)

    if args.json:
        out = dict(summary)
        if detail is not None:
            out["histogram_detail"] = {args.hist: detail}
        print(json.dumps(out, indent=2))
        return

    print_summary(summary, args.datasets)
    if detail is not None:
        print_hist_detail(args.hist, detail)


if __name__ == "__main__":
    main()
