import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker
import mplhep as hep
import sys
from scripts.coffea_file import CoffeaFile
import util

hep.style.use("CMS")


def plot_stack_with_data(sample_to_file, variable, stack_samples, data_sample, years, category, output, **kwargs):
    h_data = sample_to_file[data_sample].get_total_hist(variable, [data_sample], years, category)

    stack_hists = []
    for sample in stack_samples[::-1]:
        h = sample_to_file[sample].get_total_hist(variable, [sample], years, category)
        stack_hists.append(h)

    sf = h_data.sum().value / sum(stack_hists).sum().value
    stack_hists = [h * sf for h in stack_hists]

    label = h_data.axes[0].label
    unit = label.split("[")[1][0:-1] if "[" in label else ""
    fig, ax_stack, ax_ratio = hep.comp.data_model(
        data_hist=h_data,
        stacked_components=stack_hists,
        stacked_labels=stack_samples[::-1],
        xlabel=h_data.axes[0].label,
        ylabel=f"Entries / {h_data.axes[0].widths[0]:.1f} {unit}",
        comparison="relative_difference",
        stacked_colors=[
            "#F19EF9",
            "#FFFF7F",
            "#9268C6",
            "#80CA72",
            "#fc999a"
        ],
        h1_label="exp",
        h2_label="obs",
        marker="+",
        flow="none"
    )

    for patch in ax_stack.patches:
        patch.set_linewidth(1.5)

    for line in ax_stack.lines:
        line.remove()
    for coll in ax_stack.collections:
        coll.remove()

    hep.histplot(
        h_data,
        ax=ax_stack,
        histtype="errorbar",
        color="black",
        marker="o",
        markersize=8,
        flow="none",
        label="Data"
    )

    hep.cms.label("Preliminary", ax=ax_stack, data=True, loc=util.cms_loc_val(kwargs["cms_loc"]), lumi=kwargs["lumi"], com=kwargs["com"])
    util.apply_common_args_to_ax(ax_stack, **kwargs)
    ax_ratio.set_xlim(ax_stack.get_xlim())
    ax_ratio.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())

    handles, labels = ax_stack.get_legend_handles_labels()
    handles = [*handles[0:-2], handles[-1]]
    labels = [*labels[0:-2], labels[-1]]
    handles = [handles[-1], handles[-2], *handles[0:-2]]
    labels = [labels[-1], labels[-2], *labels[0:-2]]
    ax_stack.legend(handles, labels, loc="upper right")

    fig.savefig(output, bbox_inches="tight")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--hist", required=True)
    parser.add_argument("--category")
    parser.add_argument("--years", nargs="+")
    parser.add_argument("--stack-sample-order", nargs="+")
    parser.add_argument("--data-sample")
    util.add_common_args(parser)
    args = parser.parse_args()

    fs = [CoffeaFile(f) for f in args.inputs]

    sample_to_file = {}
    for f in fs:
        for sample in f.get_samples(args.hist):
            sample_to_file[sample] = f

    plot_stack_with_data(
        sample_to_file,
        args.hist,
        args.stack_sample_order,
        args.data_sample,
        args.years,
        args.category,
        args.output,
        xmin=args.xmin,
        xmax=args.xmax,
        ymin=args.ymin,
        ymax=args.ymax,
        xlog=args.xlog,
        ylog=args.ylog,
        xstart=args.xstart,
        xend=args.xend,
        ystart=args.ystart,
        yend=args.yend,
        cms_loc=args.cms_loc,
        lumi=args.lumi,
        com=args.com
    )


if __name__ == "__main__":
    main()
