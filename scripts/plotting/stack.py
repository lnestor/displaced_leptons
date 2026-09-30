import matplotlib.ticker
import mplhep as hep

from scripts.plotting import transforms
from scripts.plotting.common import (
    DATA_LABEL,
    PlottingInputError,
    cms_label,
    entries_label,
    finish_axes,
    sample_color,
    sample_label,
)


def order_samples(mc_hists, order=None):
    if order is None:
        return sorted(mc_hists, key=lambda sample: transforms.integral(mc_hists[sample]))

    if sorted(order) != sorted(mc_hists):
        raise PlottingInputError(
            f"order {list(order)} must contain exactly the MC samples {list(mc_hists)}"
        )
    return list(order)


def plot_stack(
    data_hist,
    mc_hists,
    order=None,
    scale_to_data=True,
    xstart=None,
    xend=None,
    lumi=None,
    com=13.6,
    cms_loc="exterior",
    **axis_options,
):
    samples = order_samples(mc_hists, order)
    colors = [sample_color(s) for s in samples]
    labels = [sample_label(s) for s in samples]

    data_hist = transforms.crop(data_hist, xstart=xstart, xend=xend)
    stack_hists = [transforms.crop(mc_hists[s], xstart=xstart, xend=xend) for s in samples]

    if scale_to_data:
        sf = transforms.integral(data_hist) / sum(transforms.integral(h) for h in stack_hists)
        stack_hists = [h * sf for h in stack_hists]

    xlabel = axis_options.pop("xlabel", None)
    if axis_options.get("ylabel") is None:
        axis_options["ylabel"] = entries_label(data_hist.axes[0])

    fig, ax_stack, ax_ratio = hep.comp.data_model(
        data_hist=data_hist,
        stacked_components=stack_hists,
        stacked_labels=labels,
        xlabel=data_hist.axes[0].label,
        ylabel=axis_options["ylabel"],
        comparison="relative_difference",
        stacked_colors=colors,
        h1_label="exp",
        h2_label="obs",
        marker="+",
        flow="none",
    )

    for patch in ax_stack.patches:
        patch.set_linewidth(1.5)

    for line in ax_stack.lines:
        line.remove()
    for coll in ax_stack.collections:
        coll.remove()

    hep.histplot(
        data_hist,
        ax=ax_stack,
        histtype="errorbar",
        color="black",
        marker="o",
        markersize=8,
        flow="none",
        label=DATA_LABEL,
    )

    cms_label(ax_stack, is_data=True, lumi=lumi, com=com, cms_loc=cms_loc)
    finish_axes(ax_stack, **axis_options)
    if xlabel is not None:
        ax_ratio.set_xlabel(xlabel)
    ax_ratio.set_xlim(ax_stack.get_xlim())
    ax_ratio.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())

    handles, all_labels = ax_stack.get_legend_handles_labels()
    by_label = dict(zip(all_labels, handles))
    extras = [label for label in by_label if label != DATA_LABEL and label not in labels]
    legend_labels = [DATA_LABEL, *extras, *labels[::-1]]
    ax_stack.legend([by_label[label] for label in legend_labels], legend_labels, loc="upper right")

    return fig, ax_stack, ax_ratio
