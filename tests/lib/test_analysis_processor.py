import awkward as ak
import pytest

from lib.workflow.analysis_processor import genweight_sums


def test_genweight_sums_without_skim_sums_genweight_and_sign():
    events = ak.Array({"genWeight": [2.0, -1.0, 3.0]})

    sumw, sum_sign = genweight_sums(events, is_skim=False)

    assert sumw == pytest.approx(4.0)
    assert sum_sign == 1


def test_genweight_sums_with_skim_applies_rescale_to_sumw_only():
    events = ak.Array({"genWeight": [2.0, -1.0, 3.0], "skimRescaleGenWeight": [2.0, 2.0, 2.0]})

    sumw, sum_sign = genweight_sums(events, is_skim=True)

    assert sumw == pytest.approx(8.0)
    assert sum_sign == 1


def test_genweight_sums_of_no_events_is_zero():
    events = ak.Array({"genWeight": [2.0]})[:0]

    sumw, sum_sign = genweight_sums(events, is_skim=False)

    assert sumw == 0
    assert sum_sign == 0
