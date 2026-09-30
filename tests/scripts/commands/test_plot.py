import hist
import pytest

from scripts.commands import plot
from scripts.plotting.common import PlottingInputError


def test_check_selection_passes_for_valid_selection(coffea_file):
    plot.check_selection(coffea_file, "h1", ["s1", "s2"], ["y1"], "c1")


def test_check_selection_unknown_hist_lists_choices(coffea_file):
    with pytest.raises(PlottingInputError, match="histogram.*\n  h1"):
        plot.check_selection(coffea_file, "missing", ["s1"], ["y1"], "c1")


def test_check_selection_unknown_sample_lists_choices(coffea_file):
    with pytest.raises(PlottingInputError, match="sample.*missing.*\n  d1\n  s1\n  s2"):
        plot.check_selection(coffea_file, "h1", ["missing"], ["y1"], "c1")


def test_check_selection_unknown_year_lists_choices(coffea_file):
    with pytest.raises(PlottingInputError, match="year.*missing.*\n  y1\n  y2"):
        plot.check_selection(coffea_file, "h1", ["s2"], ["missing"], "c1")


def test_check_selection_year_missing_from_chosen_samples(coffea_file):
    with pytest.raises(PlottingInputError, match="year.*y2"):
        plot.check_selection(coffea_file, "h1", ["s1"], ["y2"], "c1")


def test_check_selection_unknown_category_lists_choices(coffea_file):
    with pytest.raises(PlottingInputError, match="category.*missing.*\n  c1\n  c2"):
        plot.check_selection(coffea_file, "h1", ["s1"], ["y1"], "missing")


def test_load_hist_sums_samples(coffea_file):
    h = plot.load_hist(coffea_file, "h1", ["s1", "s2"], ["y1"], "c1")

    assert h.sum().value == 4


def test_load_hist_sums_years(coffea_file):
    h = plot.load_hist(coffea_file, "h1", ["s2"], ["y1", "y2"], "c1")

    assert h.sum().value == 4


def test_load_hist_errors_when_a_sample_has_no_entries_in_the_years(coffea_file):
    with pytest.raises(PlottingInputError, match="s1"):
        plot.load_hist(coffea_file, "h1", ["s1", "s2"], ["y2"], "c1")


def test_is_data_false_for_mc_samples(coffea_file):
    assert not plot.is_data(coffea_file, "h1", ["s1", "s2"])


def test_is_data_true_for_data_samples(coffea_file):
    assert plot.is_data(coffea_file, "h1", ["d1"])


def test_is_data_rejects_mixed_samples(coffea_file):
    with pytest.raises(PlottingInputError, match="mix"):
        plot.is_data(coffea_file, "h1", ["s1", "d1"])


def test_is_data_allows_mixed_samples_when_requested(coffea_file):
    assert plot.is_data(coffea_file, "h1", ["s1", "d1"], allow_mixed=True)


def _make_2d():
    return hist.Hist(
        hist.axis.Regular(2, 0, 2, name="ax1"),
        hist.axis.Regular(3, 0, 3, name="ax2"),
    )


def test_reduce_to_1d_leaves_1d_hist_unchanged(coffea_file):
    h = plot.load_hist(coffea_file, "h1", ["s1"], ["y1"], "c1")

    assert plot.reduce_to_1d(h, None) is h


def test_reduce_to_1d_requires_xvar_for_multiple_axes():
    with pytest.raises(PlottingInputError, match="xvar"):
        plot.reduce_to_1d(_make_2d(), None)


def test_reduce_to_1d_projects_onto_xvar():
    h = plot.reduce_to_1d(_make_2d(), "ax2")

    assert [ax.name for ax in h.axes] == ["ax2"]


def test_reduce_to_2d_leaves_2d_hist_unchanged_without_vars():
    h = _make_2d()

    assert plot.reduce_to_2d(h, None, None) is h


def test_reduce_to_2d_requires_both_vars_when_one_is_given():
    with pytest.raises(PlottingInputError, match="xvar"):
        plot.reduce_to_2d(_make_2d(), "ax1", None)


def test_reduce_to_2d_orders_axes_by_the_given_vars():
    h = plot.reduce_to_2d(_make_2d(), "ax2", "ax1")

    assert [ax.name for ax in h.axes] == ["ax2", "ax1"]
