"""
Lookup helper for datasets/sources/datasets.yaml.

Usage:
    from scripts.datasets.catalog import DatasetCatalog

    catalog = DatasetCatalog()
    catalog.get(sample="Muon", year="2022_preEE")
    catalog.get(sample="DY", year="2024", is_mc=True)
"""

from pathlib import Path

import yaml

DEFAULT_PATH = Path("datasets/sources/datasets.yaml")


class DatasetDefinition:
    def __init__(self, sample, miniaod, nanoaod, year, supplements_path, is_mc, era=None):
        self.sample = sample
        self.miniaod = miniaod
        self.nanoaod = nanoaod
        self.year = year
        self.supplements_path = supplements_path
        self.is_mc = is_mc
        self.era = era

    def __repr__(self):
        return (
            f"DatasetDefinition(sample={self.sample!r}, year={self.year!r}, "
            f"era={self.era!r}, is_mc={self.is_mc!r})"
        )


class DatasetCatalog:
    def __init__(self, path=DEFAULT_PATH):
        with open(path) as f:
            raw = yaml.safe_load(f)
        self.entries = [DatasetDefinition(**entry) for entry in raw]

    def get(self, sample=None, year=None, era=None, is_mc=None):
        result = self.entries
        if sample is not None:
            result = [e for e in result if e.sample == sample]
        if year is not None:
            result = [e for e in result if e.year == year]
        if era is not None:
            result = [e for e in result if e.era == era]
        if is_mc is not None:
            result = [e for e in result if e.is_mc == is_mc]
        return result

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)
