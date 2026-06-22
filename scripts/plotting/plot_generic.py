import argparse
import coffea.util
import hist
from matplotlib.colorbar import Colorbar
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
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
    get_is_data,
    get_axis_names,
    cms_loc_val
)

hep.style.use("CMS")


def plot1d(h, ax, is_data, **kwargs):
    is_multiple = isinstance(h, list)

    if kwargs["normalize"]:
        if is_multiple:
            h = [hi / hi.sum().value for hi in h]
        else:
            h = h / h.sum().value

    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=cms_loc_val(kwargs["cms_loc"]), lumi=kwargs["lumi"])
    hep.histplot(
        h,
        histtype="errorbar",
        ax=ax,
        label=kwargs["labels"] if is_multiple else None,
        flow="none" # Prevents placing a "step connection" to the first visible point
    )

    apply_common_args_to_ax(ax, **kwargs)

    h_single = h[0] if is_multiple else h
    width = h_single.axes[0].widths[0]
    unit = h_single.axes[0].label.split("[")[1][0:-1]

    label = f"Entries / {width:.1f} {unit}"
    if kwargs["normalize"]:
        label += " (Unit Area Norm.)"
    ax.set_ylabel(label)

    if is_multiple:
        ax.legend()


def plot2d(h, fig, ax, is_data, **kwargs):
    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=cms_loc_val(kwargs["cms_loc"]), lumi=kwargs["lumi"])


    if kwargs["density"]:
        x_widths = h.axes[0].widths
        y_widths = h.axes[1].widths
        areas = np.outer(x_widths, y_widths)
        h = h / areas
        colorbar_label = r"Events / $\mu m^2$"
    else:
        colorbar_label = "Events"

    norm = "log" if kwargs["heatlog"] else "linear"
    hep.hist2dplot(h, ax=ax, norm=norm, flow="none")
    fig.axes[1].set_ylabel(colorbar_label, rotation=90, labelpad=20)

    apply_common_args_to_ax(ax, **kwargs)


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

    # 1D Arguments
    parser.add_argument("--split-axis")
    parser.add_argument("--normalize", action="store_true")

    # 2D Arguments
    parser.add_argument("--heatlog", action="store_true", help="Use logarithmic colorbar scale for 2D histograms")
    parser.add_argument("--density", action="store_true", help="Scale 2D histogram by bin area (events / area)")

    add_common_args(parser)
    args = parser.parse_args()

    print(f"Loading {args.input}")
    f = coffea.util.load(args.input)

    valid_hists = get_variables(f)
    if not args.hist in valid_hists:
        print(f"\nUnknown histogram '{args.hist}' selected."
               " Choose from:\n  {0}\n".format("\n  ".join(valid_hists)))
        sys.exit(1)

    valid_samples = get_samples(f, args.hist)
    if args.sample and args.sample not in valid_samples:
        print(f"\nUnknown sample '{args.sample}' selected."
               " Choose from:\n  {0}".format("\n  ".join(valid_samples)))
        sys.exit(1)
    elif not args.sample:
        samples = valid_samples
        print(f"Sample not provided."
               " Will combine all:\n  {0}".format("\n  ".join(valid_samples)))
    else:
        # TODO: support multiple samples pass in
        samples = [args.sample]
        print(f"Using sample: {args.sample}")

    # Assume all samples have same year for now
    valid_years = get_years(f, args.hist, samples[0])
    if args.years and any(y not in valid_years for y in args.years):
        invalid_years = [y for y in args.years if not y in valid_years]
        print(f"\nUnknown year(s) '{' '.join(invalid_years)}' selected."
               "Choose from:\n  {0}".format("\n  ".join(sorted(valid_years))))
        sys.exit(1)
    elif not args.years:
        years = valid_years
        print(f"Years not provided."
               " Will combine all:\n  {0}".format("\n  ".join(valid_years)))
    else:
        years = args.years
        print(f"Using years: {' '.join(sorted(args.years))}")
    datasets = get_datasets(f, args.hist, samples[0], years)

    # Assume all datasets have the same categories
    valid_cats = get_categories(f, args.hist, samples[0], datasets[0])
    if args.category and not args.category in valid_cats:
        print(f"\nUnknown category '{args.category}' selected."
               " Choose from:\n  {0}".format("\n  ".join(valid_cats)))
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

    dims = len(h.axes)
    if args.split_axis is not None:
        dims -= 1

    if dims == 1:
        # Warn if xvar doesn't match only axis
        # Warn if yvar is passed
        pass
    else:
        axis_names = get_axis_names(h)
        if args.xvar is None:
            print(f"\nX-Variable not provided for {dims}-d histogram."
                  " Choose from:\n  {0}".format("\n  ".join(axis_names)))
            sys.exit(1)
        elif args.xvar not in axis_names:
            print(f"\nUnknown x-variable '{args.xvar}' selected."
                  " Choose from:\n  {0}".format("\n  ".join(axis_names)))
            sys.exit(1)
        elif args.yvar is None:
            h = h.project(args.xvar)
        elif args.yvar not in axis_names:
            # TODO: don't show the selected x axis to use in output
            print(f"\nUnknown y-variable '{args.yvar}' selected."
                  " Choose from:\n  {0}".format("\n  ".join(axis_names)))
            sys.exit(1)
        else:
            h = h.project(args.xvar, args.yvar)

    # TODO: Applying normalize here would be nice, but I'm not sure that is an option
    # if we have split hists. Perhaps we can apply normalize here and then move this
    # inside the if statements
    h = apply_common_args_to_hist(h, **kwargs)
    fig, ax = plt.subplots()

    if args.split_axis:
        # Hist should only be 2D at this point.
        h_list = []
        labels = []

        split_ax_idx = next(i for i, ax in enumerate(h.axes) if ax.name == args.split_axis)
        split_ax = h.axes[split_ax_idx]
        x_ax_name = next(ax.name for ax in h.axes if ax.name != args.split_axis)

        for bin_idx in range(len(split_ax.edges) - 1):
            edges = split_ax.bin(bin_idx)
            label = f"${edges[0]} <$ {split_ax.label} $< {edges[1]}$"
            if split_ax_idx == 0:
                h_proj = h[bin_idx, :].project(x_ax_name)
            else:
                h_proj = h[:, bin_idx].project(x_ax_name)

            h_list.append(h_proj)
            labels.append(label)

        kwargs["labels"] = labels
        plot1d(h_list, ax, is_data, **kwargs)
    elif len(h.axes) == 1:
        plot1d(h, ax, is_data, **kwargs)
    else:
        plot2d(h, fig, ax, is_data, **kwargs)

    fig.savefig(args.output, bbox_inches="tight")


if __name__ == "__main__":
    main()
