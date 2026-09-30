import coffea.util
import hist
import pytest

from scripts.coffea_file import CoffeaFile

LAYOUT = {
    "s1": ("True", ["y1"]),
    "s2": ("True", ["y1", "y2"]),
    "d1": ("False", ["y1"]),
}


@pytest.fixture
def coffea_file(tmp_path):
    variables = {"h1": {}}
    by_dataset = {}

    for sample, (is_mc, years) in LAYOUT.items():
        for year in years:
            key = f"{sample}_{year}"
            h = hist.Hist(
                hist.axis.StrCategory(["c1", "c2"], name="cat"),
                hist.axis.Regular(4, 0, 4, name="ax1"),
                storage=hist.storage.Weight(),
            )
            h.fill(cat="c1", ax1=[0.5, 1.5])
            variables["h1"].setdefault(sample, {})[key] = h
            by_dataset[key] = {"year": year, "isMC": is_mc}

    path = tmp_path / "file.coffea"
    coffea.util.save(
        {"variables": variables, "datasets_metadata": {"by_dataset": by_dataset}}, path
    )
    return CoffeaFile(str(path))
