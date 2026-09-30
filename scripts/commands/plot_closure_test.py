import argparse
import os

import matplotlib.pyplot as plt

from scripts.coffea_file import CoffeaFile
from scripts.plotting import transforms
from scripts.plotting.hist1d import plot_1d
from scripts.plotting.hist2d import plot_2d

LINTHRESH = 5e-4
INDEPENDENCE_HISTS = ("lxy_vs_lxy",)
PULL_LIMIT = 3

HIST_STYLES_BY_NAME = {
    "InteractionPoint_r": ("1d", dict(ylog=True)),
    "InteractionPoint_x_vs_y": ("2d", dict()),
    "lxy_vs_lxy": ("2d", dict(heatlog=True, xlog=True, ylog=True, xlinthresh=LINTHRESH, ylinthresh=LINTHRESH)),
    "d0_vs_d0": ("2d", dict(heatlog=True)),
}

HIST_STYLES_BY_SUFFIX = {
    "_lxy": ("1d", dict(xlog=True, ylog=True, xlinthresh=LINTHRESH)),
    "_dx_vs_dy": ("2d", dict(heatlog=True, xlog=True, ylog=True, xlinthresh=LINTHRESH, ylinthresh=LINTHRESH)),
    "_parentpt_vs_lxy": ("2d", dict(heatlog=True, ylog=True, ylinthresh=LINTHRESH)),
    "_parentpt_vs_d0": ("2d", dict(heatlog=True)),
}


def get_style(hist_name):
    if hist_name in HIST_STYLES_BY_NAME:
        return HIST_STYLES_BY_NAME[hist_name]
    for suffix in sorted(HIST_STYLES_BY_SUFFIX, key=len, reverse=True):
        if hist_name.endswith(suffix):
            return HIST_STYLES_BY_SUFFIX[suffix]
    return None


def plot_independence(h, sample, com, **options):
    fig, axes = plt.subplots(1, 3, figsize=(30, 8))
    common = dict(is_data=False, com=com)

    plot_2d(h, ax=axes[0], text=f"Actual ({sample})", **common, **options)
    plot_2d(
        transforms.expected_if_independent(h),
        ax=axes[1],
        text="Expected if independent",
        **common,
        **options,
    )
    plot_2d(
        transforms.independence_pull(h),
        ax=axes[2],
        text="Pull",
        zlabel="(actual - expected) / sqrt(expected)",
        cmap="RdBu_r",
        zmin=-PULL_LIMIT,
        zmax=PULL_LIMIT,
        **common,
        **{**options, "heatlog": False},
    )

    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Merged closure test coffea file")
    parser.add_argument("--output-dir", help="Defaults to a plots/ directory next to the input file")
    parser.add_argument("--samples", help="Comma-separated samples, e.g. DY__ee,DY__mumu. Defaults to all samples")
    parser.add_argument("--years", help="Comma-separated years. Defaults to all years")
    parser.add_argument("--category", default="baseline")
    parser.add_argument("--com", type=float, default=13.6)
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(os.path.dirname(args.input), "plots")
    os.makedirs(output_dir, exist_ok=True)

    requested_samples = args.samples.split(",") if args.samples else None
    years = args.years.split(",") if args.years else None

    f = CoffeaFile(args.input)

    for hist_name in f.hist_names():
        style = get_style(hist_name)
        if style is None:
            print(f"Skipping {hist_name}: no plot style defined")
            continue
        kind, options = style

        for sample in f.get_samples(hist_name):
            if requested_samples is not None and sample not in requested_samples:
                continue

            h = f.get_total_hist(hist_name, samples=sample, years=years, category=args.category)
            plot = plot_1d if kind == "1d" else plot_2d
            fig, _ = plot(h, is_data=False, com=args.com, **options)

            output_path = os.path.join(output_dir, f"{hist_name}_{sample}.png")
            fig.savefig(output_path, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved {output_path}")

            if hist_name in INDEPENDENCE_HISTS:
                fig = plot_independence(h, sample, args.com, **options)
                output_path = os.path.join(output_dir, f"{hist_name}_independence_check_{sample}.png")
                fig.savefig(output_path, bbox_inches="tight")
                plt.close(fig)
                print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
