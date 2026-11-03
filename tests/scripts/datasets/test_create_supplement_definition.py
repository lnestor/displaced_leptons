from types import SimpleNamespace

from create_supplement_definition import find_duplicated_lumis, get_supplement_definition, merge_definitions


def make_definition(files, rejected_lumis=None):
    definition = {"metadata": {"dataset": "ds1", "sample": "s1", "year": "y1", "version": 1}, "files": files}
    if rejected_lumis is not None:
        definition["rejected_lumis"] = rejected_lumis
    return definition


def test_find_duplicated_lumis_reports_lumi_in_more_than_one_file():
    file_to_lumis = {"f1": [(1, 1), (1, 2)], "f2": [(1, 2), (1, 3)]}

    assert find_duplicated_lumis(file_to_lumis) == [[1, 2]]


def test_find_duplicated_lumis_ignores_lumi_listed_twice_in_one_file():
    file_to_lumis = {"f1": [(1, 1), (1, 1)], "f2": [(1, 2)]}

    assert find_duplicated_lumis(file_to_lumis) == []


def test_find_duplicated_lumis_returns_sorted_list():
    file_to_lumis = {"f1": [(2, 1), (1, 5)], "f2": [(2, 1), (1, 5)]}

    assert find_duplicated_lumis(file_to_lumis) == [[1, 5], [2, 1]]


def test_get_supplement_definition_writes_rejected_lumis_when_given():
    dataset_def = SimpleNamespace(nanoaod="ds1", sample="s1", year="y1", era=None)

    supp_def = get_supplement_definition(dataset_def, {}, {}, 1, rejected_lumis=[])

    assert supp_def["rejected_lumis"] == []


def test_get_supplement_definition_omits_rejected_lumis_when_not_given():
    dataset_def = SimpleNamespace(nanoaod="ds1", sample="s1", year="y1", era=None)

    supp_def = get_supplement_definition(dataset_def, {}, {}, 1)

    assert "rejected_lumis" not in supp_def


def test_merge_definitions_combines_rejected_lumis():
    existing = make_definition({"c1": ["s1"]}, rejected_lumis=[[1, 2], [1, 5]])
    new = make_definition({"c2": ["s2"]}, rejected_lumis=[[1, 3], [1, 5]])

    merged = merge_definitions(existing, new)

    assert merged["rejected_lumis"] == [[1, 2], [1, 3], [1, 5]]


def test_merge_definitions_omits_rejected_lumis_when_neither_has_them():
    merged = merge_definitions(make_definition({"c1": ["s1"]}), make_definition({"c2": ["s2"]}))

    assert "rejected_lumis" not in merged
