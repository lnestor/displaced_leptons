from pathlib import Path
import yaml

DEFAULT_PATH = Path("datasets/sources/datasets.yaml")


class DatasetDefinition:
    def __init__(self, sample, miniaod, nanoaod, year, supplements_path, is_mc, type, key, cross_section=None, era=None, index=None, version=None):
        self.sample = sample
        self.type = type
        self.key = key
        self.miniaod = miniaod
        self.nanoaod = nanoaod
        self.year = year
        self.supplements_path = supplements_path
        self.is_mc = is_mc
        self.era = era
        self.xsec = cross_section
        self.index = index
        self.version = version

    def __repr__(self):
        return (
            f"DatasetDefinition(key={self.key!r}, sample={self.sample!r}, year={self.year!r}, "
            f"era={self.era!r}, is_mc={self.is_mc!r})"
        )


class DatasetCatalog:
    def __init__(self, path=DEFAULT_PATH):
        with open(path) as f:
            raw = yaml.safe_load(f)
        self.entries = [DatasetDefinition(**entry) for entry in raw]

    def get(self, sample=None, year=None, era=None, is_mc=None):
        def matches(value, filter_value):
            if filter_value is None:
                return True
            if isinstance(filter_value, (list, tuple, set)):
                return value in filter_value
            return value == filter_value

        return [
            e for e in self.entries
            if matches(e.sample, sample)
            and matches(e.year, year)
            and matches(e.era, era)
            and matches(e.is_mc, is_mc)
        ]

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)
