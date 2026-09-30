import hist
import numpy as np

from scripts.plotting.common import PlottingInputError


def _loc(value):
    return None if value is None else hist.loc(value)


def crop(h, xstart=None, xend=None, ystart=None, yend=None):
    bounds = [(xstart, xend), (ystart, yend)]
    if len(h.axes) == 1 and ystart is None and yend is None:
        bounds = bounds[:1]
    elif len(h.axes) != len(bounds):
        raise PlottingInputError(f"Cannot crop a {len(h.axes)}-d histogram")

    if all(value is None for bound in bounds for value in bound):
        return h

    return h[tuple(slice(_loc(lo), _loc(hi)) for lo, hi in bounds)]


def rebin(h, factor):
    return h[tuple(slice(None, None, hist.rebin(factor)) for _ in h.axes)]


def integral(h):
    total = h.sum(flow=False)
    return getattr(total, "value", total)


def normalize(h):
    return h / integral(h)


def divide_by_bin_area(h):
    areas = np.outer(*[axis.widths for axis in h.axes])
    out = h.copy()
    view = out.view()
    if hasattr(view, "value"):
        view.value = view.value / areas
        view.variance = view.variance / areas ** 2
    else:
        view[...] = view / areas
    return out


def project(h, *names):
    axis_names = [axis.name for axis in h.axes]
    for name in names:
        if name not in axis_names:
            raise PlottingInputError(
                f"Unknown axis '{name}'. Choose from:\n  " + "\n  ".join(axis_names)
            )
    return h.project(*names)


def split_by_axis(h, name):
    if len(h.axes) != 2:
        raise PlottingInputError(f"Splitting needs a 2-d histogram, got {len(h.axes)}-d")

    axis_names = [axis.name for axis in h.axes]
    if name not in axis_names:
        raise PlottingInputError(
            f"Unknown axis '{name}'. Choose from:\n  " + "\n  ".join(axis_names)
        )

    idx = axis_names.index(name)
    axis = h.axes[idx]
    hists = [h[{idx: i}] for i in range(len(axis))]
    labels = [f"{lo:g} < {axis.label} < {hi:g}" for lo, hi in (axis.bin(i) for i in range(len(axis)))]
    return hists, labels


def weighted_mean_profile(h2d):
    values = h2d.values()
    variances = h2d.variances()
    centers = h2d.axes[1].centers

    total = values.sum(axis=1)
    mean = (values * centers).sum(axis=1) / total
    variance = (variances * (centers - mean[:, None]) ** 2).sum(axis=1) / total ** 2

    h_profile = hist.Hist(h2d.axes[0], storage=hist.storage.Weight())
    view = h_profile.view()
    view.value = mean
    view.variance = variance

    return h_profile


def cdf(h):
    values = np.cumsum(h.values())
    out = hist.Hist(h.axes[0], storage=hist.storage.Weight())
    view = out.view()
    view.value = values / values[-1]
    view.variance = np.zeros_like(values)
    return out


def _with_values(h, value, variance):
    out = h.copy()
    view = out.view()
    if hasattr(view, "value"):
        view.value = value
        view.variance = variance
    else:
        view[...] = value
    return out


def expected_if_independent(h):
    values = h.values()
    expected = np.outer(values.sum(axis=1), values.sum(axis=0)) / values.sum()
    return _with_values(h, expected, expected)


def independence_pull(h, min_expected=1.0):
    values = h.values()
    expected = expected_if_independent(h).values()

    pull = np.zeros_like(values)
    mask = expected > min_expected
    pull[mask] = (values[mask] - expected[mask]) / np.sqrt(expected[mask])
    return _with_values(h, pull, np.ones_like(pull))
