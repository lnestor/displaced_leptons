import argparse
import coffea.util
import hist
import matplotlib.pyplot as plt
import mplhep as hep
import pathlib

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
    fig, ax_stack, ax_comp = hep.comp.data_model(
        data_hist = compare_hist,
        stacked_components = stack_hists,
        stacked_labels = stack[::-1],
        xlabel=compare_hist.axes[0].label,
        ylabel=f"Entries / {compare_hist.axes[0].widths[0]:.1f} {unit}",
        comparison="relative_difference",
        flow="none" # Prevents placing a "step connection" on x axis
    )
    hep.cms.label("Preliminary", ax=ax_stack, data=True, loc=1) # loc=1 is top left interior

    if kwargs["xlim"][0] is not None:
        ax_stack.set_xlim(left=kwargs["xlim"][0])

    if kwargs["xlim"][1] is not None:
        ax_stack.set_xlim(right=kwargs["xlim"][1])

    if kwargs["ylim"][0] is not None:
        ax_stack.set_ylim(bottom=kwargs["ylim"][0])

    if kwargs["ylim"][1] is not None:
        ax_stack.set_ylim(top=kwargs["ylim"][1])

    if kwargs["xlog"]:
        ax_stack.set_xscale("log")

    if kwargs["ylog"]:
        ax_stack.set_yscale("log")

    ax_stack.legend(loc="lower left")
    fig.savefig(output)

def plot_stack(root, output, variable, year, category, stack, **kwargs):
    hists = {}
    for group_name in stack[::-1]:
        samples = [_extract_full_sample_name(name, root, variable) for name in _ALIASES[group_name]]
        hists[group_name] = _combine_hists(root, variable, samples, year, category, False)

    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=True, loc=1) # loc=1 is top left interior
    hep.histplot(
        list(hists.values()),
        histtype="fill",
        stack=True,
        label=stack[::-1],
        ax=ax
    )

    if kwargs["xlim"][0] is not None:
        ax.set_xlim(left=kwargs["xlim"][0])

    if kwargs["xlim"][1] is not None:
        ax.set_xlim(right=kwargs["xlim"][1])

    if kwargs["ylim"][0] is not None:
        ax.set_ylim(bottom=kwargs["ylim"][0])

    if kwargs["ylim"][1] is not None:
        ax.set_ylim(top=kwargs["ylim"][1])

    if kwargs["xlog"]:
        ax.set_xscale("log")

    if kwargs["ylog"]:
        ax.set_yscale("log")

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
    parser.add_argument("--xmin", type=float, default=None)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=None)
    parser.add_argument("--ymax", type=float, default=None)
    parser.add_argument("--xlog", action="store_true")
    parser.add_argument("--ylog", action="store_true")
    parser.add_argument("--xstart", type=float, default=None)
    parser.add_argument("--compare-file", type=pathlib.Path)
    parser.add_argument("--compare-sample")
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
            xstart=args.xstart
        )
    else:
        plot_stack(
            f,
            args.output,
            args.variable,
            args.year,
            args.category,
            args.stack,
            compare_f,
            args.compare_sample,
            xlim=(args.xmin, args.xmax),
            ylim=(args.ymin, args.ymax),
            xlog=args.xlog,
            ylog=args.ylog,
            xstart=args.xstart
        )


if __name__ == "__main__":
    main()
