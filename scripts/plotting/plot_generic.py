import argparse
import coffea.util
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import mplhep as hep
import sys
from util import (
    add_common_args,
    apply_common_args_to_ax,
    apply_common_args_to_hist,
    get_variables,
    get_samples,
    get_years,
    get_datasets,
    get_categories,
    get_combined_hist,
    get_is_data
)

hep.style.use("CMS")


def plot(h, output, is_data, **kwargs):
    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=1) # loc=1 is top left interior
    hep.histplot(
        h,
        histtype="errorbar",
        ax=ax,
        markersize=8,
        marker="o",
        color="black",
        flow="none" # Prevents placing a "step connection" to the first visible point
    )

    apply_common_args_to_ax(ax, **kwargs)

    unit = h.axes[0].label.split("[")[1][0:-1]
    ax.set_ylabel(f"Entries / {h.axes[0].widths[0]:.1f} {unit}")

    fig.savefig(output)


def plot2d(h, output, is_data, **kwargs):
    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=1) # loc=1 is top left interior
    hep.hist2dplot(h, ax=ax, norm=LogNorm())

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, 200000)
    ax.set_ylim(1, 200000)
    ticks = [100, 500, 100000]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.xaxis.set_major_formatter(plt.ScalarFormatter())
    ax.yaxis.set_major_formatter(plt.ScalarFormatter())

    apply_common_args_to_ax(ax, **kwargs)

    fig.savefig(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to .coffea file")
    parser.add_argument("hist", help="Name of the histogram to plot")

    parser.add_argument("-c", "--category")
    parser.add_argument("-y", "--years", nargs="+")
    parser.add_argument("-s", "--sample")

    parser.add_argument("-o", "--output", default="plot.png", help="Output filename.")

    parser.add_argument("--xvar", help="Name of the variable to plot on the xaxis for 2D histograms")
    parser.add_argument("--yvar", help="Name of the varaible to plot on the yaxis for 2D histograms")

    add_common_args(parser)
    # parser.add_argument("-n", "--normalize", action="store_true")
    # parser.add_argument("-ps", "--plot-separately", action="store_true")
    args = parser.parse_args()

    print(f"Loading {args.input}")
    f = coffea.util.load(args.input)

    valid_hists = get_variables(f)
    if not args.hist in valid_hists:
        print(f"\nUnknown histogram '{args.hist}' selected."
              f" Choose from:\n  {'\n  '.join(valid_hists)}\n")
        sys.exit(1)
    
    valid_samples = get_samples(f, args.hist)
    if args.sample and args.sample not in valid_samples:
        print(f"\nUnknown sample '{args.sample}' selected."
              f" Choose from:\n  {'\n  '.join(valid_samples)}")
        sys.exit(1)
    elif not args.sample:
        samples = valid_samples
        print(f"Sample not provided."
              f" Will combine all:\n  {'\n  '.join(valid_samples)}")
    else:
        # TODO: support multiple samples pass in
        samples = [args.sample]
        print(f"Using sample: {args.sample}")

    # Assume all samples have same year for now
    valid_years = get_years(f, args.hist, samples[0])
    if args.years and any(y not in valid_years for y in args.years):
        invalid_years = [y for y in args.years if not y in valid_years]
        print(f"\nUnknown year(s) '{' '.join(invalid_years)}' selected."
              f"Choose from:\n  {'\n  '.join(sorted(valid_years))}")
        sys.exit(1)
    elif not args.years:
        years = valid_years
        print(f"Years not provided."
              f" Will combine all:\n  {'\n  '.join(valid_years)}")
    else:
        years = args.years
        print(f"Using years: {' '.join(sorted(args.years))}")
    datasets = get_datasets(f, args.hist, samples[0], years)

    # Assume all datasets have the same categories
    valid_cats = get_categories(f, args.hist, samples[0], datasets[0])
    if args.category and not args.category in valid_cats:
        print(f"\nUnknown category '{args.category}' selected."
              f" Choose from:\n  {'\n  '.join(valid_cats)}")
        sys.exit(1)
    elif not args.category:
        print("No category chosen. Defauling to baseline category")
        category = "baseline"
    else:
        print(f"Using category: {args.category}")
        category = args.category

    is_data_list = [get_is_data(f, d) for d in datasets]
    if all(is_data_list):
        is_data = True
    elif any(is_data_list):
        print("mixed MC and data datasets chosen")
        sys.exit(1)
    else:
        is_data = False

    h = get_combined_hist(f, args.hist, samples, datasets, category, is_data)

    kwargs = vars(args).copy()
    kwargs.pop("output", None)

    # TODO: integrate axes based on xvar/yvar
    # Warn if 2D arguments were supplied

    # h = apply_common_args_to_hist(h, **kwargs)

    if len(h.axes) == 1:
        plot(h, args.output, is_data, **kwargs)
    else:
        h = h.project("e1_d0", "mu1_d0")
        plot2d(h, args.output, is_data, **kwargs)


if __name__ == "__main__":
    main()

# TODO: if axis min is 0 and also set to log, error and tell user
# add 1e6 syntax to axis args
# lumi label argument - number for now, but also could read from a script with a keyword
# Extract markersize/color etc. into styles
# Add argument to start plotting at some point
