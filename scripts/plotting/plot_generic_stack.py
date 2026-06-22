import argparse
import coffea.util
import hist
import matplotlib.pyplot as plt
import mplhep as hep
import pathlib

import util as plot_util

hep.style.use("CMS")

_ALIASES = {
    "DY": ["DYJetsToLL_M-10to50", "DYJetsToLL_M-50"],
    "ttbar": ["TTToSemiLeptonic", "TTTo2L2Nu", "TTToHadronic"],
    "singletop": ["ST_tW_top", "ST_t-channel_top", "ST_tW_antitop", "ST_t-channel_antitop", "ST_s-channel"],
    "diboson": ["WZ", "ZZ", "WW"]
}


def _get_hist(root, variable, sample, year_key, category, is_data):
    if is_data:
        return root["variables"][variable][sample][year_key][category, :]
    else:
        return root["variables"][variable][sample][year_key][category, "nominal", :]


def _combine_hists(root, variable, samples, year, category, is_data):
    combined = None
    for sample in samples:
        for year_key in root["variables"][variable][sample]:
            if year in year_key:
                h = _get_hist(root, variable, sample, year_key, category, is_data)

                if combined is None:
                    combined = h
                else:
                    combined += h
    return combined


def _extract_full_sample_name(short_name, root, variable):
    for full_name in root["variables"][variable].keys():
        if short_name in full_name:
            return full_name



def plot_compare(stack_root, compare_root, output, variable, year, category, stack, compare_sample, **kwargs):
    compare_hist = _combine_hists(compare_root, variable, [compare_sample], year, category, True)

    stack_hists = []
    for group_name in stack[::-1]:
        samples = [_extract_full_sample_name(name, stack_root, variable) for name in _ALIASES[group_name]]
        stack_hists.append(_combine_hists(stack_root, variable, samples, year, category, False))

    total_stack = sum(stack_hists)
    stack_integral = total_stack.sum().value
    compare_integral = compare_hist.sum().value
    sf = compare_integral / stack_integral
    stack_hists = [h * sf for h in stack_hists]

    unit = compare_hist.axes[0].label.split("(")[1][0:-1]
    fig, ax_stack, ax_ratio = hep.comp.data_model(
        data_hist=compare_hist,
        stacked_components=stack_hists,
        stacked_labels=stack[::-1],
        xlabel=compare_hist.axes[0].label,
        ylabel=f"Entries / {compare_hist.axes[0].widths[0]:.1f} {unit}",
        comparison="relative_difference",
        stacked_colors=[
            "#F19EF9",
            "#FFFF7F",
            "#9268C6",
            "#80CA72"
        ],
        h1_label="exp",
        h2_label="obs",
        marker="+", # Marker for ratio plot
        flow="none" # Prevents placing a "step connection" on x axis
    )

    # Make the lines between stacked histograms thicker
    for patch in ax_stack.patches:
        patch.set_linewidth(1.5)

    # hep.comp.data_model doesn't allow for styling the data histogram
    # To get around that, we remove it and redraw it with our custom styling
    for line in ax_stack.lines:
        line.remove() # Removes data points

    for coll in ax_stack.collections:
        coll.remove() # Removes data error bars

    hep.histplot(
        compare_hist,
        ax=ax_stack,
        histtype="errorbar",
        color="black",
        marker="o",
        markersize=8,
        flow="none",
        label="Data"
    )

    hep.cms.label("Preliminary", ax=ax_stack, data=True, loc=1, lumi=kwargs["lumi"]) # loc=1 is top left interior
    plot_util.apply_common_args(ax_stack, **kwargs)

    # We want the Data label to be on the top of the legend
    handles, labels = ax_stack.get_legend_handles_labels()
    # Remove the data_model data legend entry since it has wrong marker style
    handles = [*handles[0:-2], handles[-1]]
    labels = [*labels[0:-2], labels[-1]]
    # Rearrange so data/MC unc. is first
    handles = [handles[-1], handles[-2], *handles[0:-2]]
    labels = [labels[-1], labels[-2], *labels[0:-2]]
    ax_stack.legend(handles, labels, loc="lower left")

    fig.savefig(output)

def plot_stack(root, output, variable, year, category, stack, **kwargs):
    hists = {}
    for group_name in stack[::-1]:
        samples = [_extract_full_sample_name(name, root, variable) for name in _ALIASES[group_name]]
        hists[group_name] = _combine_hists(root, variable, samples, year, category, False)

    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=True, loc=1, lumi=kwargs["lumi"]) # loc=1 is top left interior
    hep.histplot(
        list(hists.values()),
        histtype="fill",
        stack=True,
        label=stack[::-1],
        ax=ax
    )

    plot_util.apply_common_args(ax, **kwargs)

    ax.legend(loc="upper right")
    fig.savefig(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to .coffea file")
    parser.add_argument("-o", "--output", help="Output filename. Defaults to <DEFUALT")
    parser.add_argument("-v", "--variable", required=True)
    parser.add_argument("-c", "--category")
    parser.add_argument("-y", "--year")
    parser.add_argument("-s", "--stack", nargs="+")
    parser.add_argument("--compare-file", type=pathlib.Path)
    parser.add_argument("--compare-sample")
    plot_util.add_common_args(parser)
    args = parser.parse_args()

    print(f"Loading {args.input}")
    f = coffea.util.load(args.input)

    if args.compare_file:
        print(f"Loading {args.compare_file}")
        compare_f = coffea.util.load(args.compare_file)

        plot_compare(
            f,
            compare_f,
            args.output,
            args.variable,
            args.year,
            args.category,
            args.stack,
            args.compare_sample,
            xlim=(args.xmin, args.xmax),
            ylim=(args.ymin, args.ymax),
            xlog=args.xlog,
            ylog=args.ylog,
            xstart=args.xstart,
            lumi=args.lumi
        )
    else:
        plot_stack(
            f,
            args.output,
            args.variable,
            args.year,
            args.category,
            args.stack,
            xlim=(args.xmin, args.xmax),
            ylim=(args.ymin, args.ymax),
            xlog=args.xlog,
            ylog=args.ylog,
            lumi=args.lumi
        )


if __name__ == "__main__":
    main()
