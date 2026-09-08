import awkward as ak
import numpy as np
import pytest

from lib.awkward_helper import JoinMismatchError, create_key, join, match_indices, trim_to_shortest


def test_create_key_extracts_values_for_requested_fields_only():
    arr = ak.Array({"key1": [1, 1, 2], "key2": [10, 20, 30], "key3": [0, 0, 0]})

    key = create_key(arr, ["key1", "key2"])

    assert "key3" not in key.dtype.names
    np.testing.assert_array_equal(key["key1"], [1, 1, 2])
    np.testing.assert_array_equal(key["key2"], [10, 20, 30])


def test_match_indices_with_empty_right_matches_nothing():
    left = ak.Array({"key": [1, 2, 3]})
    right = ak.Array({"key": np.array([], dtype=np.int64)})

    right_idx, matched_mask = match_indices(left, right, ["key"])

    assert len(right_idx) == 0
    np.testing.assert_array_equal(matched_mask, [False, False, False])


def test_match_indices_composite_key_requires_all_fields_to_match():
    left = ak.Array({"key1": [1, 2], "key2": [10, 20]})
    right = ak.Array({"key1": [1, 2], "key2": [10, 99]})

    right_idx, matched_mask = match_indices(left, right, ["key1", "key2"])

    np.testing.assert_array_equal(matched_mask, [True, False])
    np.testing.assert_array_equal(right_idx, [0])


def test_match_indices_returns_matched_indices():
    left = ak.Array({"key": [1, 2, 3, 4]})
    right = ak.Array({"key": [3, 1]})

    right_idx, matched_mask = match_indices(left, right, ["key"])

    np.testing.assert_array_equal(matched_mask, [True, False, True, False])
    np.testing.assert_array_equal(right_idx, [1, 0])


def test_trim_to_shortest_trims_left_when_left_has_more_objects():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[30, 20, 10]], "field2": [[0.1, 0.2, 0.3]]})})
    right = ak.Array({"key": [1], "coll_field1": [[35]], "coll_field2": [[0.15]]})

    left, right = trim_to_shortest(left, right, ["coll"], ["key"])

    assert left["coll"]["field1"].tolist() == [[30]]
    assert left["coll"]["field2"].tolist() == [[0.1]]
    assert right["coll_field1"].tolist() == [[35]]
    assert right["coll_field2"].tolist() == [[0.15]]


def test_trim_to_shortest_trims_right_and_all_its_fields_when_right_has_more_objects():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[15]], "field2": [[0.5]]})})
    right = ak.Array({"key": [1], "coll_field1": [[25, 22, 21]], "coll_field2": [[0.55, 0.56, 0.57]]})

    left, right = trim_to_shortest(left, right, ["coll"], ["key"])

    assert left["coll"]["field1"].tolist() == [[15]]
    assert right["coll_field1"].tolist() == [[25]]
    assert right["coll_field2"].tolist() == [[0.55]]


def test_trim_to_shortest_leaves_unmatched_rows_untouched():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[8, 4]], "field2": [[0.7, 0.8]]})})
    right = ak.Array({"key": [99], "coll_field1": [[1, 2, 3, 4, 5]], "coll_field2": [[0.71, 0.72, 0.73, 0.74, 0.75]]})

    left, right = trim_to_shortest(left, right, ["coll"], ["key"])

    assert left["coll"]["field1"].tolist() == [[8, 4]]
    assert right["coll_field1"].tolist() == [[1, 2, 3, 4, 5]]


def test_trim_to_shortest_skips_collection_with_no_matching_branches():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[10]], "field2": [[0.1]]})})
    right = ak.Array({"key": [1], "coll_field1": [[10]], "coll_field2": [[0.1]]})

    left, right = trim_to_shortest(left, right, ["other_coll"], ["key"])

    assert left["coll"]["field1"].tolist() == [[10]]
    assert right["coll_field1"].tolist() == [[10]]


def test_join_drops_unmatched_rows_and_merges_a_new_collection():
    left = ak.Array({"key": [1, 2, 3], "val": [100, 200, 300]})
    right = ak.Array({"key": [1, 3], "coll_field1": [[10], [30]]})

    result = join(left, right, ["key"])

    assert result["key"].tolist() == [1, 3]
    assert result["val"].tolist() == [100, 300]
    assert result["coll"]["field1"].tolist() == [[10], [30]]


def test_join_adds_new_subfield_to_an_existing_collection():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[10]]})})
    right = ak.Array({"key": [1], "coll_field2": [[99]]})

    result = join(left, right, ["key"])

    assert result["coll"]["field1"].tolist() == [[10]]
    assert result["coll"]["field2"].tolist() == [[99]]


def test_join_skips_counter_branches_without_an_underscore():
    left = ak.Array({"key": [1]})
    right = ak.Array({"key": [1], "ncoll": [5]})

    result = join(left, right, ["key"])

    assert result.fields == ["key"]
    assert result["key"].tolist() == [1]


def test_join_raises_on_mismatched_object_counts_for_an_existing_collection():
    left = ak.Array({"key": [1], "coll": ak.zip({"field1": [[10, 20]]})})
    right = ak.Array({"key": [1], "coll_field2": [[99]]})

    with pytest.raises(JoinMismatchError) as exc_info:
        join(left, right, ["key"])

    e = exc_info.value
    assert e.field == "coll_field2"
    assert e.coll == "coll"
    assert e.row == 0
    assert e.key_values == {"key": 1}
    assert e.left_count == 2
    assert e.right_count == 1
