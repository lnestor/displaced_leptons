import argparse
import os

import hist
import matplotlib.pyplot as plt

from scripts.coffea_file import CoffeaFile
from scripts.plotting import transforms
from scripts.plotting.common import SAMPLE_LABELS, PlottingInputError
from scripts.plotting.hist1d import plot_1d
from scripts.plotting.hist2d import plot_2d
from scripts.plotting.stack import plot_stack

AXIS_KEYS = (
    "xmin", "xmax", "ymin", "ymax", "xlog", "ylog", "xlinthresh", "ylinthresh",
    "xlabel", "ylabel", "text",
)
STYLE_KEYS = ("lumi", "com", "cms_loc")


def common_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("input", help="A .coffea file")
    parser.add_argument("hist", help="Name of the histogram to plot")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-y", "--years", nargs="+", required=True)
    parser.add_argument("-c", "--category", default="baseline")
    parser.add_argument("--xvar", help="Axis to project onto when the histogram has extra axes")
    parser.add_argument("--xmin", type=float)
    parser.add_argument("--xmax", type=float)
    parser.add_argument("--ymin", type=float)
    parser.add_argument("--ymax", type=float)
    parser.add_argument("--xstart", type=float, help="Crop the histogram to start at this x value")
    parser.add_argument("--xend", type=float, help="Crop the histogram to end at this x value")
    parser.add_argument("--xlog", action="store_true")
    parser.add_argument("--ylog", action="store_true")
    parser.add_argument("--xlinthresh", type=float, help="Use symlog on x with this threshold")
    parser.add_argument("--ylinthresh", type=float, help="Use symlog on y with this threshold")
    parser.add_argument("--xlabel")
    parser.add_argument("--ylabel")
    parser.add_argument("--text", help="Annotation in the top left of the axes")
    parser.add_argument("--lumi", type=float, help="Integrated luminosity in fb^-1")
    parser.add_argument("--com", type=float, default=13.6, help="Center-of-mass energy in TeV")
    parser.add_argument("--cms-loc", choices=["interior", "exterior"], default="exterior")
    return parser


def build_parser():
    parser = argparse.ArgumentParser(description="One-off plots from a merged coffea file")
    sub = parser.add_subparsers(dest="kind", required=True)
    common = common_parser()

    p1 = sub.add_parser("1d", parents=[common], help="1D histogram")
    p1.add_argument("-s", "--samples", nargs="+", required=True)
    p1.add_argument("--overlay", action="store_true", help="Draw each sample separately")
    p1.add_argument("--split-axis", help="Overlay the slices of this axis of a 2D histogram")
    p1.add_argument("--normalize", action="store_true")
    p1.add_argument("--rebin", type=int)
    p1.add_argument("--histtype", choices=["errorbar", "step", "fill"], default="errorbar")

    p2 = sub.add_parser("2d", parents=[common], help="2D histogram")
    p2.add_argument("-s", "--samples", nargs="+", required=True)
    p2.add_argument("--yvar", help="Second axis to project onto")
    p2.add_argument("--ystart", type=float)
    p2.add_argument("--yend", type=float)
    p2.add_argument("--heatlog", action="store_true", help="Logarithmic color scale")
    p2.add_argument("--density", action="store_true", help="Divide by bin area")
    p2.add_argument("--zlabel", help="Colorbar label")

    ps = sub.add_parser("stack", parents=[common], help="Stacked MC compared to data")
    ps.add_argument("--mc-samples", nargs="+", required=True)
    ps.add_argument("--data-sample", required=True)
    ps.add_argument("--order", nargs="+", help="MC samples from bottom to top of the stack")
    ps.add_argument("--no-scale-to-data", action="store_true")

    return parser


def pick(args, keys):
    return {key: getattr(args, key) for key in keys}


def samples_of(args):
    if args.kind == "stack":
        return [args.data_sample, *args.mc_samples]
    return args.samples


def check_choice(kind, values, valid):
    invalid = [v for v in values if v not in valid]
    if invalid:
        raise PlottingInputError(
            f"Unknown {kind}(s) {' '.join(invalid)}. Choose from:\n  " + "\n  ".join(sorted(valid))
        )


def check_selection(f, hist_name, samples, years, category):
    if f.has_hist(hist_name, samples, years, category):
        return

    check_choice("histogram", [hist_name], f.hist_names())
    check_choice("sample", samples, f.get_samples(hist_name))
    valid_years = {y for s in samples for y in f.get_years(hist_name, s)}
    check_choice("year", years, valid_years)
    check_choice("category", [category], f.get_categories(hist_name))


def load_hist(f, hist_name, samples, years, category):
    total = None
    for sample in samples:
        h = f.get_total_hist(hist_name, samples=[sample], years=years, category=category)
        if not isinstance(h, hist.Hist):
            raise PlottingInputError(f"No entries for sample '{sample}' in years {' '.join(years)}")
        total = h if total is None else total + h
    return total


def is_data(f, hist_name, samples, allow_mixed=False):
    flags = [f.is_data(s, hist_name) for s in samples]
    if any(flags) and not all(flags) and not allow_mixed:
        raise PlottingInputError("Cannot mix data and MC samples in one histogram")
    return any(flags)


def reduce_to_1d(h, xvar):
    if len(h.axes) == 1:
        return h
    if xvar is None:
        raise PlottingInputError("--xvar is required for a histogram with more than one axis")
    return transforms.project(h, xvar)


def reduce_to_2d(h, xvar, yvar):
    if len(h.axes) == 2 and xvar is None and yvar is None:
        return h
    if xvar is None or yvar is None:
        raise PlottingInputError("--xvar and --yvar are both required to select 2 axes")
    return transforms.project(h, xvar, yvar)


def run_1d(args, f):
    def load(samples):
        return load_hist(f, args.hist, samples, args.years, args.category)

    if args.split_axis:
        h = load(args.samples)
        if len(h.axes) > 2:
            if args.xvar is None:
                raise PlottingInputError("--xvar is required to split a histogram with more than 2 axes")
            h = transforms.project(h, args.xvar, args.split_axis)
        hists, labels = transforms.split_by_axis(h, args.split_axis)
    elif args.overlay:
        hists = [reduce_to_1d(load([s]), args.xvar) for s in args.samples]
        labels = [SAMPLE_LABELS.get(s, s) for s in args.samples]
    else:
        hists = [reduce_to_1d(load(args.samples), args.xvar)]
        labels = None

    fig, _ = plot_1d(
        hists,
        labels=labels,
        histtype=args.histtype,
        normalize=args.normalize,
        rebin=args.rebin,
        xstart=args.xstart,
        xend=args.xend,
        is_data=is_data(f, args.hist, args.samples, allow_mixed=args.overlay),
        **pick(args, STYLE_KEYS),
        **pick(args, AXIS_KEYS),
    )
    return fig


def run_2d(args, f):
    h = load_hist(f, args.hist, args.samples, args.years, args.category)
    fig, _ = plot_2d(
        reduce_to_2d(h, args.xvar, args.yvar),
        heatlog=args.heatlog,
        density=args.density,
        zlabel=args.zlabel,
        xstart=args.xstart,
        xend=args.xend,
        ystart=args.ystart,
        yend=args.yend,
        is_data=is_data(f, args.hist, args.samples),
        **pick(args, STYLE_KEYS),
        **pick(args, AXIS_KEYS),
    )
    return fig


def run_stack(args, f):
    if not is_data(f, args.hist, [args.data_sample]):
        raise PlottingInputError(f"'{args.data_sample}' is not a data sample")
    if is_data(f, args.hist, args.mc_samples, allow_mixed=True):
        raise PlottingInputError("--mc-samples must not contain data samples")

    def load(sample):
        return reduce_to_1d(load_hist(f, args.hist, [sample], args.years, args.category), args.xvar)

    fig, _, _ = plot_stack(
        load(args.data_sample),
        {s: load(s) for s in args.mc_samples},
        order=args.order,
        scale_to_data=not args.no_scale_to_data,
        xstart=args.xstart,
        xend=args.xend,
        **pick(args, STYLE_KEYS),
        **pick(args, AXIS_KEYS),
    )
    return fig


RUNNERS = {"1d": run_1d, "2d": run_2d, "stack": run_stack}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        f = CoffeaFile(args.input)
        check_selection(f, args.hist, samples_of(args), args.years, args.category)
        fig = RUNNERS[args.kind](args, f)
    except PlottingInputError as err:
        parser.error(str(err))

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
