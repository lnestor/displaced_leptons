import os
import glob
import cloudpickle
localdir = os.path.dirname(os.path.abspath(__file__))

from pocket_coffea.parameters import defaults
default_parameters = defaults.get_default_parameters()
defaults.register_configuration_dir("config_dir", f"{localdir}/params")

parameters = defaults.merge_parameters_from_files(
    default_parameters,
    f"{localdir}/params/object_preselection.yaml",
    f"{localdir}/params/triggers.yaml",
    f"{localdir}/params/plotting.yaml",
    f"{localdir}/params/categories.yaml",
    update=True
)

import workflow
import event_selection
import object_selection
import lib.named_cut as named_cut
cloudpickle.register_pickle_by_value(workflow)
cloudpickle.register_pickle_by_value(event_selection)
cloudpickle.register_pickle_by_value(object_selection)
cloudpickle.register_pickle_by_value(named_cut)

from workflow import DisplacedLeptonProcessor
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_dilepton_deltaR,
    get_no_in_material_vtx,
    MUON_FLAVOR,
    ELECTRON_FLAVOR,
)
from lib.named_cut import NamedCut

from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_functions import get_HLTsel
from pocket_coffea.parameters.cuts import passthrough

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": [f for f in glob.glob(f"{localdir}/datasets/cmssw/*.json")],
        "filter": {
            "samples": ["MuonEG"],
            "samples_exclude": [],
            "year": ["2018"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    calibrators = [],
    skim = [
        NamedCut(cut=get_HLTsel(primaryDatasets=["EMu"]), label="Stage00_Trigger"),
    ],
    preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0),                          label="Stage14_CosAlpha"),
        NamedCut(cut=get_min_muon_delta_t(-20),                             label="Stage15_DeltaT"),
        NamedCut(cut=get_dilepton_deltaR("emu", 0.2),                       label="Stage16_DeltaR"),
        NamedCut(cut=get_no_in_material_vtx(MUON_FLAVOR, ELECTRON_FLAVOR),  label="Stage17_NoDispVtx"),
    ],
    categories = {
        "baseline": [passthrough],
    },
    weights = {
        "common": {
            "inclusive": [
                "genWeight",
                "lumi",
                "XS",
            ],
            "bycategory": {}
        },
        "bysample": {}
    },
    variations = {
        "weights": {
            "common": {
                "inclusive": [],
                "bycategory": {}
            },
            "bysample": {}
        }
    },
    variables = {},
)
