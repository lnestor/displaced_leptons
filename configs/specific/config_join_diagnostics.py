import numpy as np

from configs.common import (
    RUN_3_YEARS,
    get_params,
    get_datasets,
    get_supplements,
    get_default_skim_cuts,
    register_modules,
)

from lib.workflow.join_diagnostic_processor import JoinDiagnosticProcessor
from lib.configurator import Configurator
from pocket_coffea.parameters.histograms import HistConf, Axis
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.lib.cut_definition import Cut
from pocket_coffea.lib.columns_manager import ColOut

register_modules()


def _mismatch_impl(events, params, **kwargs):
    diff = events[params["field"]]
    return ~np.isnan(diff) & (diff != 0)


def get_mismatch_cut(field):
    return Cut(name=f"{field}_nonzero", params={"field": field}, function=_mismatch_impl)


muon_mismatch_cut = get_mismatch_cut("muonCountDiff")
electron_mismatch_cut = get_mismatch_cut("electronCountDiff")

cfg = Configurator(
    parameters = get_params(),
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", "MuonEG", "Muon"],
            "year": RUN_3_YEARS
        }
    },
    supplements = get_supplements(),
    workflow = JoinDiagnosticProcessor,
    skim = get_default_skim_cuts(),
    custom_fields = {},
    object_selections = {},
    event_preselections = [],
    categories = {
        "baseline": [passthrough],
        "muon_mismatch": [muon_mismatch_cut],
        "electron_mismatch": [electron_mismatch_cut],
    },
    hists = {
        "nMuon": HistConf([Axis(field="nMuon", bins=10, start=0, stop=10, label="# Central Muons")], only_categories=["baseline"]),
        "nElectron": HistConf([Axis(field="nElectron", bins=10, start=0, stop=10, label="# Central Electrons")], only_categories=["baseline"]),
        "nSupplementMuon": HistConf([Axis(field="nSupplementMuon", bins=10, start=0, stop=10, label="# Supplement Muons")], only_categories=["baseline"]),
        "nSupplementElectron": HistConf([Axis(field="nSupplementElectron", bins=10, start=0, stop=10, label="# Supplement Electrons")], only_categories=["baseline"]),
        "muonCountDiff": HistConf([Axis(field="muonCountDiff", bins=20, start=-10, stop=10, label="# Muon Difference (central-supplement)")], only_categories=["baseline"]),
        "electronCountDiff": HistConf([Axis(field="electronCountDiff", bins=20, start=-10, stop=10, label="# Electron Difference (central-supplement)")], only_categories=["baseline"]),
    },
    workflow_options = {"dump_columns_as_arrays_per_chunk": "root://cmseos.fnal.gov//store/user/lnestor/columns_output/"},
    columns = {
        "common": {
            "bycategory": {
                "muon_mismatch": [ColOut(
                    collection="events",
                    columns=["run", "luminosityBlock", "event", "nMuon", "nSupplementMuon", "muonCountDiff"],
                )],
                "electron_mismatch": [ColOut(
                    collection="events",
                    columns=["run", "luminosityBlock", "event", "nElectron", "nSupplementElectron", "electronCountDiff"],
                )],
            }
        }
    }
)
