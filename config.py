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
import hists
import channel_selection
import lib.named_cut as named_cut
cloudpickle.register_pickle_by_value(workflow)
cloudpickle.register_pickle_by_value(event_selection)
cloudpickle.register_pickle_by_value(object_selection)
cloudpickle.register_pickle_by_value(hists)
cloudpickle.register_pickle_by_value(channel_selection)
cloudpickle.register_pickle_by_value(named_cut)

from workflow import DisplacedLeptonProcessor
from event_selection import get_nLeptonGood, get_d0_lt
from channel_selection import ee_cuts, mumu_cuts, emu_veto, emu_cuts

from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_functions import get_HLTsel, goldenJson, eventFlags, get_nObj_min, get_nPVgood
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from pocket_coffea.parameters.cuts import passthrough

from pocket_coffea.parameters.histograms import HistConf, Axis

from hists import lepton_hists, background_hists
from named_cut import NamedCut

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": [f for f in glob.glob(f"{localdir}/datasets/central/*.json")],
        "filter": {
            "samples": [
                "MuonEG",
                "Muon",
                "EGamma",
                "DoubleMuon",
                "DY",
                "TTbar",
                "SingleTop",
                "Diboson",
                "QCD_Ele",
                "QCD_Mu"
            ],
            "samples_exclude": [],
            "year": [
                "2022_preEE",
                "2022_postEE",
                "2023_preBPix",
                "2023_postBPix",
                "2024",
                "2025"
            ]
        }
    },
    workflow = DisplacedLeptonProcessor,
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator],
    skim = [
        NamedCut(cut=eventFlags, label="MET Filters"),
        NamedCut(cut=goldenJson, label="Golden JSON"),
        NamedCut(cut=get_HLTsel(), label="Passes triggers")
    ],
    preselections = [],
    categories = {
        "baseline": [passthrough],
        "ee": [*ee_cuts(parameters), emu_veto(parameters)],
        "ee_pcr": [*ee_cuts(parameters), emu_veto(parameters), get_d0_lt("ElectronGood", 50, 0), get_d0_lt("ElectronGood", 50, 1)],
        "emu": [*emu_cuts(parameters)],
        "emu_pcr": [*emu_cuts(parameters), get_d0_lt("ElectronGood", 50, 0), get_d0_lt("MuonGood", 50, 0)],
        "mumu": [*mumu_cuts(parameters), emu_veto(parameters)],
        "mumu_pcr": [*mumu_cuts(parameters), emu_veto(parameters), get_d0_lt("MuonGood", 50, 0), get_d0_lt("MuonGood", 50, 1)],
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
    variables = {
        **lepton_hists(coll="ElectronGood", label="Electron"),
        **lepton_hists(coll="MuonGood", label="Muon"),
        **background_hists()
    }
)
