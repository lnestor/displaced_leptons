import hist
import mplhep as hep

from scripts.plotting import transforms
from scripts.plotting.common import cms_label, entries_label, finish_axes, get_fig_ax


def plot_1d(
    hists,
    labels=None,
    ax=None,
    histtype="errorbar",
    normalize=False,
    rebin=None,
    xstart=None,
    xend=None,
    is_data=True,
    lumi=None,
    com=13.6,
    cms_loc="exterior",
    **axis_options,
):
    if isinstance(hists, hist.Hist):
        hists = [hists]

    hists = [transforms.crop(h, xstart=xstart, xend=xend) for h in hists]
    if rebin:
        hists = [transforms.rebin(h, rebin) for h in hists]
    if normalize:
        hists = [transforms.normalize(h) for h in hists]

    if axis_options.get("ylabel") is None:
        axis_options["ylabel"] = entries_label(hists[0].axes[0], normalized=normalize)
    if axis_options.get("ylog") and not any((h.values() > 0).any() for h in hists):
        axis_options["ylog"] = False

    fig, ax = get_fig_ax(ax)
    cms_label(ax, is_data=is_data, lumi=lumi, com=com, cms_loc=cms_loc)
    hep.histplot(hists, histtype=histtype, ax=ax, label=labels, flow="none")

    if labels:
        ax.legend()

    finish_axes(ax, **axis_options)
    return fig, ax
