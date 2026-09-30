def test_has_hist_true_for_valid_selection(coffea_file):
    assert coffea_file.has_hist("h1", ["s1", "s2"], ["y1"], "c1")


def test_has_hist_true_with_only_the_hist_name(coffea_file):
    assert coffea_file.has_hist("h1")


def test_has_hist_accepts_single_sample_and_year_strings(coffea_file):
    assert coffea_file.has_hist("h1", "s2", "y2", "c2")


def test_has_hist_false_for_unknown_hist(coffea_file):
    assert not coffea_file.has_hist("missing")


def test_has_hist_false_for_unknown_sample(coffea_file):
    assert not coffea_file.has_hist("h1", ["s1", "missing"])


def test_has_hist_false_for_unknown_year(coffea_file):
    assert not coffea_file.has_hist("h1", years=["missing"])


def test_has_hist_false_for_year_missing_from_the_chosen_samples(coffea_file):
    assert not coffea_file.has_hist("h1", ["s1"], ["y2"])


def test_has_hist_false_for_unknown_category(coffea_file):
    assert not coffea_file.has_hist("h1", category="missing")
