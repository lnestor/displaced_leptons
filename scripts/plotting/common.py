import re

import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

SAMPLE_COLORS = {
    "TTbar": "#9268C6",
    "Diboson": "#FFFF7F",
    "SingleTop": "#F19EF9",
    "DY": "#80CA72",
    "QCDEle": "#FC999A",
    "QCDMu": "#FFCC99",
}

SAMPLE_LABELS = {
    "TTbar": r"$t\overline{t}$",
    "Diboson": "Diboson",
    "SingleTop": "Single top",
    "DY": "DY",
    "QCDEle": "EM-enriched QCD",
    "QCDMu": r"$\mu$-enriched QCD",
}

DATA_LABEL = "Data"

CMS_LOC = {"interior": 1, "exterior": 0}


class PlottingInputError(ValueError):
    pass


def sample_color(sample):
    if sample not in SAMPLE_COLORS:
        raise PlottingInputError(f"No color defined for sample '{sample}' in SAMPLE_COLORS")
    return SAMPLE_COLORS[sample]


def sample_label(sample):
    if sample not in SAMPLE_LABELS:
        raise PlottingInputError(f"No label defined for sample '{sample}' in SAMPLE_LABELS")
    return SAMPLE_LABELS[sample]


def axis_unit(axis):
    match = re.search(r"\[(.*)\]\s*$", axis.label or "")
    return match.group(1) if match else ""


def entries_label(axis, normalized=False):
    label = f"Entries / {axis.widths[0]:g} {axis_unit(axis)}".rstrip()
    if normalized:
        label += " (Unit Area Norm.)"
    return label


def get_fig_ax(ax=None):
    if ax is None:
        return plt.subplots()
    return ax.figure, ax


def cms_label(ax, is_data=True, lumi=None, com=13.6, cms_loc="exterior"):
    hep.cms.label(
        "Preliminary",
        ax=ax,
        data=is_data,
        loc=CMS_LOC[cms_loc],
        lumi=lumi,
        com=com,
    )


def _set_scale(set_scale, log, linthresh):
    if not log:
        return
    if linthresh is None:
        set_scale("log")
    else:
        set_scale("symlog", linthresh=linthresh)


def finish_axes(
    ax,
    xmin=None,
    xmax=None,
    ymin=None,
    ymax=None,
    xlog=False,
    ylog=False,
    xlinthresh=None,
    ylinthresh=None,
    xlabel=None,
    ylabel=None,
    text=None,
):
    _set_scale(ax.set_xscale, xlog, xlinthresh)
    _set_scale(ax.set_yscale, ylog, ylinthresh)
    if xmin is not None or xmax is not None:
        ax.set_xlim(left=xmin, right=xmax)
    if ymin is not None or ymax is not None:
        ax.set_ylim(bottom=ymin, top=ymax)

    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if text is not None:
        ax.text(0.03, 0.97, text, transform=ax.transAxes, ha="left", va="top")
