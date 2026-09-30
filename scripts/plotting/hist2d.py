import matplotlib.colors
import mplhep as hep

from scripts.plotting import transforms
from scripts.plotting.common import cms_label, finish_axes, get_fig_ax


def plot_2d(
    h,
    ax=None,
    heatlog=False,
    density=False,
    zlabel=None,
    cmap=None,
    zmin=None,
    zmax=None,
    xstart=None,
    xend=None,
    ystart=None,
    yend=None,
    is_data=True,
    lumi=None,
    com=13.6,
    cms_loc="exterior",
    **axis_options,
):
    h = transforms.crop(h, xstart=xstart, xend=xend, ystart=ystart, yend=yend)
    if density:
        h = transforms.divide_by_bin_area(h)

    if zlabel is None:
        zlabel = "Events / bin area" if density else "Events"

    fig, ax = get_fig_ax(ax)
    cms_label(ax, is_data=is_data, lumi=lumi, com=com, cms_loc=cms_loc)

    use_log = heatlog and (h.values() > 0).any()
    norm_class = matplotlib.colors.LogNorm if use_log else matplotlib.colors.Normalize
    kwargs = {} if cmap is None else {"cmap": cmap}
    artists = hep.hist2dplot(
        h, ax=ax, norm=norm_class(vmin=zmin, vmax=zmax), flow="none", **kwargs
    )
    artists.cbar.set_label(zlabel, rotation=90, labelpad=20)

    finish_axes(ax, **axis_options)
    return fig, ax
