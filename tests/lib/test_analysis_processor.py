import awkward as ak
import pytest

from lib.workflow.analysis_processor import genweight_sums, sort_by_pt


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


def _events():
    return ak.Array({
        "coll1": [[{"pt": 10.0, "field1": 1}, {"pt": 30.0, "field1": 2}, {"pt": 20.0, "field1": 3}], []],
        "coll2": [[{"pt": 5.0, "field1": 4}, {"pt": 15.0, "field1": 5}], [{"pt": 7.0, "field1": 6}]],
    })


def test_sort_by_pt_orders_collection_by_descending_pt():
    out = sort_by_pt(_events(), ["coll1"])

    assert out.coll1.pt.tolist() == [[30.0, 20.0, 10.0], []]


def test_sort_by_pt_moves_other_fields_with_their_object():
    out = sort_by_pt(_events(), ["coll1"])

    assert out.coll1.field1.tolist() == [[2, 3, 1], []]


def test_sort_by_pt_records_position_before_sorting():
    out = sort_by_pt(_events(), ["coll1"])

    assert out.coll1.original_idx.tolist() == [[1, 2, 0], []]


def test_sort_by_pt_sorts_every_listed_collection():
    out = sort_by_pt(_events(), ["coll1", "coll2"])

    assert out.coll2.pt.tolist() == [[15.0, 5.0], [7.0]]


def test_sort_by_pt_leaves_unlisted_collections_unchanged():
    out = sort_by_pt(_events(), ["coll1"])

    assert out.coll2.pt.tolist() == [[5.0, 15.0], [7.0]]
    assert "original_idx" not in out.coll2.fields


def test_sort_by_pt_does_not_modify_input_events():
    events = _events()

    sort_by_pt(events, ["coll1"])

    assert events.coll1.pt.tolist() == [[10.0, 30.0, 20.0], []]
    assert "original_idx" not in events.coll1.fields


def test_sort_by_pt_output_unaffected_by_field_reset_on_input():
    events = _events()
    out = sort_by_pt(events, ["coll1"])

    events["coll1", "pt"] = ak.Array([[1.0, 2.0, 3.0], []])

    assert out.coll1.pt.tolist() == [[30.0, 20.0, 10.0], []]
