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
cloudpickle.register_pickle_by_value(workflow)
cloudpickle.register_pickle_by_value(event_selection)
cloudpickle.register_pickle_by_value(object_selection)
cloudpickle.register_pickle_by_value(hists)

from workflow import DisplacedLeptonProcessor
from event_selection import dilepton_presel, no_b2b_muons, dilepton_pair, get_nElectrons, get_nMuons

from omegaconf import OmegaConf
from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.lib.cut_functions import get_HLTsel, goldenJson, eventFlags, get_nObj_min, get_nPVgood
from pocket_coffea.lib.calibrators.common import default_calibrators_sequence
from pocket_coffea.parameters.cuts import passthrough

from pocket_coffea.parameters.histograms import HistConf, Axis

from hists import lepton_hists

cfg = Configurator(
    parameters = parameters,
    datasets = {
        "jsons": [f for f in glob.glob(f"{localdir}/datasets/built/*.json") if "_redirector" not in f],
        "filter": {
            "samples_exclude": [],
            "year": ["2017", "2018"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    calibrators = default_calibrators_sequence,
    skim = [
        eventFlags,
        goldenJson,
        get_nPVgood(1),
        get_HLTsel(primaryDatasets=["EMu"])
    ],
    preselections = [dilepton_presel],
    categories = CartesianSelection(
        multicuts = [
            Multicut(
                name = "channel",
                cuts = [
                    ee_channel(),
                    emu_channel(),
                    mumu_channel()
                ],
                cut_names = ["ee", "emu", "mumu"]
            ),
            Multicut(
                name="region",
                cuts = [
                    lepton_d0_cuts(50, None, 50, None),
                    lepton_d0_cuts(100, 10000, 100, 10000),
                ]
                cut_names = ["prompt_CR", "SR"]
            )
        ],
        common_cats = {
            "baseline": [passthrough],
        }
    ),
    categories = {
        "emu": [no_b2b_muons, dilepton_pair("emu", 0.2), get_nElectrons(1, OmegaConf.to_container(parameters.categories.emu.Electron)), get_nMuons(1, OmegaConf.to_container(parameters.categories.emu.Muon))],
        "mumu": [no_b2b_muons, dilepton_pair("mumu", 0.2), get_nMuons(2, OmegaConf.to_container(parameters.categories.mumu.Muon))],
        "ee": [dilepton_pair("ee", 0.2), get_nElectrons(2, OmegaConf.to_container(parameters.categories.ee.Electron))]
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
    }
)
