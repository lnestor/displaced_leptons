import argparse
import coffea.util
import hist
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

def _get_hist(root, variable, sample, year_key, category, is_data):
    if is_data:
        return root["variables"][variable][sample][year_key][category, :]
    else:
        return root["variables"][variable][sample][year_key][category, "nominal", :]

def _combine_hists(root, variable, sample, year, category, is_data):
    combined = None
    for year_key in root["variables"][variable][sample]:
        if year in year_key:
            h = _get_hist(root, variable, sample, year_key, category, is_data)

            if combined is None:
                combined = h
            else:
                combined += h

    return combined

def plot(root, output, variable, sample, year, category, is_data, **kwargs):
    h = _combine_hists(root, variable, sample, year, category, is_data)

    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=1) # loc=1 is top left interior
    hep.histplot(
        h[hist.loc(0 if kwargs["xstart"] is None else kwargs["xstart"]):],
        histtype="errorbar",
        ax=ax,
        markersize=8,
        marker="o",
        color="black",
        flow="none" # Prevents placing a "step connection" to the first visible point
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

    unit = h.axes[0].label.split("[")[1][0:-1]
    ax.set_ylabel(f"Entries / {h.axes[0].widths[0]:.1f} {unit}")

    fig.savefig(output)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to .coffea file")
    parser.add_argument("-o", "--output", help="Output filename. Defaults to <DEFUALT")
    parser.add_argument("-v", "--variable", required=True)
    parser.add_argument("-c", "--category")
    parser.add_argument("-y", "--year")
    parser.add_argument("-s", "--sample")
    parser.add_argument("--xmin", type=float, default=None)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=None)
    parser.add_argument("--ymax", type=float, default=None)
    parser.add_argument("--xlog", action="store_true")
    parser.add_argument("--ylog", action="store_true")
    parser.add_argument("--xstart", type=float, default=None)
    # parser.add_argument("-n", "--normalize", action="store_true")
    # parser.add_argument("-ps", "--plot-separately", action="store_true")
    args = parser.parse_args()

    print(f"Loading {args.input}")
    f = coffea.util.load(args.input)

    valid_vars = f["variables"].keys()
    if args.variable not in valid_vars:
        parser.error(f"Unknown variable: {args.variable}. Choose from {', '.join(valid_vars)}")

    """
    samples = valid_samples = f["variables"][args.variable].keys()
    if args.sample is None:
        print(f"Sample not provided. Using all: {', '.join(valid_samples)}")
    else:
        if args.sample not in valid_samples:
            parser.error(f"Unknown sample: {args.sample}. Choose from {', '.join(valid_samples)}")
        else:
            print(f"Using sample {args.sample}")
            samples = [args.sample]

    # For now: assume all years are present on all samples
    years = valid_years = f["variables"][args.variable][samples[0]].keys()
    if args.year is None:
        print(f"Year not provided. Using all: {', '.join(valid_years)}")
    else:
        if args.year not in valid_years:
            parser.error(f"Unknown year: {args.year}. Choose from {', '.join(valid_years)}")
        else:
            print(f"Using year {args.year}")
            years = [args.year]
    """

    # Validate categories

    plot(
        f,
        args.output,
        args.variable,
        args.sample,
        args.year,
        args.category,
        True,
        # normalize=args.normalize,
        xlim=(args.xmin, args.xmax),
        ylim=(args.ymin, args.ymax),
        xlog=args.xlog,
        ylog=args.ylog,
        xstart=args.xstart,
    )


if __name__ == "__main__":
    main()

# TODO: if axis min is 0 and also set to log, error and tell user
# add 1e6 syntax to axis args
# lumi label argument - number for now, but also could read from a script with a keyword
# Extract markersize/color etc. into styles
# Add argument to start plotting at some point
