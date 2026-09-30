import hist
import numpy as np
import pytest

from scripts.plotting import transforms
from scripts.plotting.common import PlottingInputError


def _make_1d(values, lo=0, hi=None, name="ax1"):
    hi = len(values) if hi is None else hi
    h = hist.Hist(hist.axis.Regular(len(values), lo, hi, name=name), storage=hist.storage.Weight())
    h.view().value = np.asarray(values, dtype=float)
    h.view().variance = np.asarray(values, dtype=float)
    return h


def _make_2d(values):
    values = np.asarray(values, dtype=float)
    h = hist.Hist(
        hist.axis.Regular(values.shape[0], 0, values.shape[0], name="ax1"),
        hist.axis.Regular(values.shape[1], 0, values.shape[1], name="ax2"),
        storage=hist.storage.Weight(),
    )
    h.view().value = values
    h.view().variance = values
    return h


def test_crop_keeps_only_bins_inside_range():
    h = _make_1d([1, 2, 3, 4, 5, 6])

    cropped = transforms.crop(h, xstart=2, xend=5)

    np.testing.assert_array_equal(cropped.values(), [3, 4, 5])


def test_crop_open_ended_range():
    h = _make_1d([1, 2, 3, 4, 5, 6])

    cropped = transforms.crop(h, xstart=4)

    np.testing.assert_array_equal(cropped.values(), [5, 6])


def test_crop_without_bounds_returns_input_unchanged():
    h = _make_1d([1, 2, 3])

    assert transforms.crop(h) is h


def test_crop_2d_crops_each_axis_independently():
    h = _make_2d(np.arange(12).reshape(3, 4))

    cropped = transforms.crop(h, xstart=1, ystart=2)

    np.testing.assert_array_equal(cropped.values(), [[6, 7], [10, 11]])


def test_crop_1d_rejects_y_bounds():
    h = _make_1d([1, 2, 3])

    with pytest.raises(PlottingInputError):
        transforms.crop(h, ystart=1)


def test_rebin_sums_adjacent_bins():
    h = _make_1d([1, 2, 3, 4, 5, 6])

    rebinned = transforms.rebin(h, 2)

    np.testing.assert_array_equal(rebinned.values(), [3, 7, 11])


def test_normalize_gives_unit_integral():
    h = _make_1d([1, 2, 3, 4])

    normalized = transforms.normalize(h)

    assert transforms.integral(normalized) == pytest.approx(1.0)


def test_normalize_scales_variance_with_value():
    h = _make_1d([2, 6])

    normalized = transforms.normalize(h)

    np.testing.assert_allclose(normalized.variances(), [2 / 64, 6 / 64])


def test_integral_ignores_flow_bins():
    h = _make_1d([1, 2, 3])
    h.fill([-5, 100])

    assert transforms.integral(h) == pytest.approx(6.0)


def test_divide_by_bin_area_scales_values_and_variances():
    h = hist.Hist(
        hist.axis.Variable([0, 1, 3], name="ax1"),
        hist.axis.Variable([0, 2, 6], name="ax2"),
        storage=hist.storage.Weight(),
    )
    h.view().value = np.full((2, 2), 8.0)
    h.view().variance = np.full((2, 2), 8.0)

    out = transforms.divide_by_bin_area(h)

    np.testing.assert_allclose(out.values(), [[4, 2], [2, 1]])
    np.testing.assert_allclose(out.variances(), [[2, 0.5], [0.5, 0.125]])


def test_divide_by_bin_area_does_not_modify_input():
    h = _make_2d(np.full((2, 2), 4.0))

    transforms.divide_by_bin_area(h)

    np.testing.assert_array_equal(h.values(), np.full((2, 2), 4.0))


def test_project_returns_named_axis():
    h = _make_2d([[1, 2], [3, 4]])

    projected = transforms.project(h, "ax2")

    np.testing.assert_array_equal(projected.values(), [4, 6])


def test_project_unknown_axis_lists_choices():
    h = _make_2d([[1, 2], [3, 4]])

    with pytest.raises(PlottingInputError, match="ax1"):
        transforms.project(h, "missing")


def test_split_by_axis_returns_one_hist_per_bin():
    h = _make_2d([[1, 2, 3], [4, 5, 6]])

    hists, labels = transforms.split_by_axis(h, "ax1")

    assert len(hists) == 2
    np.testing.assert_array_equal(hists[1].values(), [4, 5, 6])
    assert len(labels) == 2


def test_split_by_axis_labels_bin_edges():
    h = _make_2d([[1, 2], [3, 4]])
    h.axes[1].label = "field"

    _, labels = transforms.split_by_axis(h, "ax2")

    assert labels == ["0 < field < 1", "1 < field < 2"]


def test_split_by_axis_rejects_non_2d():
    h = _make_1d([1, 2, 3])

    with pytest.raises(PlottingInputError):
        transforms.split_by_axis(h, "ax1")


def test_weighted_mean_profile_gives_mean_along_second_axis():
    h = _make_2d([[0, 2, 2], [4, 0, 0]])

    profile = transforms.weighted_mean_profile(h)

    np.testing.assert_allclose(profile.values(), [2.0, 0.5])


def test_cdf_is_cumulative_and_ends_at_one():
    h = _make_1d([1, 1, 2])

    out = transforms.cdf(h)

    np.testing.assert_allclose(out.values(), [0.25, 0.5, 1.0])


def test_expected_if_independent_matches_a_factorized_hist():
    values = np.outer([1, 2], [3, 1, 2]).astype(float)
    h = _make_2d(values)

    expected = transforms.expected_if_independent(h)

    np.testing.assert_allclose(expected.values(), values)


def test_expected_if_independent_preserves_the_total():
    h = _make_2d([[5, 1, 0], [2, 7, 3]])

    expected = transforms.expected_if_independent(h)

    assert transforms.integral(expected) == pytest.approx(transforms.integral(h))


def test_expected_if_independent_does_not_modify_input():
    h = _make_2d([[5, 1], [2, 7]])

    transforms.expected_if_independent(h)

    np.testing.assert_array_equal(h.values(), [[5, 1], [2, 7]])


def test_independence_pull_is_zero_for_a_factorized_hist():
    h = _make_2d(np.outer([10, 20], [30, 10, 20]).astype(float))

    pull = transforms.independence_pull(h)

    np.testing.assert_allclose(pull.values(), 0, atol=1e-12)


def test_independence_pull_is_signed_and_scaled_by_sqrt_expected():
    h = _make_2d([[30, 10], [10, 30]])

    pull = transforms.independence_pull(h)

    np.testing.assert_allclose(pull.values(), [[10 / 20 ** 0.5, -10 / 20 ** 0.5], [-10 / 20 ** 0.5, 10 / 20 ** 0.5]])


def test_independence_pull_is_zero_where_expected_is_small():
    h = _make_2d([[100, 0], [0, 1]])

    pull = transforms.independence_pull(h)

    assert pull.values()[1, 1] == 0
