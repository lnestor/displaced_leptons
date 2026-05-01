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
cloudpickle.register_pickle_by_value(workflow)
cloudpickle.register_pickle_by_value(event_selection)
cloudpickle.register_pickle_by_value(object_selection)
cloudpickle.register_pickle_by_value(hists)
cloudpickle.register_pickle_by_value(channel_selection)

from workflow import DisplacedLeptonProcessor
from event_selection import dilepton_presel, d0_cuts
from channel_selection import ee_channel, emu_channel, mumu_channel, emu_veto

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
            "samples": [
                "DYJetsToLL_M-10to50_TuneCP5_13TeV-madgraphMLM-pythia8",
                "DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8",
                # "QCD_Pt-1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-120To170_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-120to170_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-15To20_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-15to20_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-170To300_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-170to300_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-20To30_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-20to30_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-300To470_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-300toInf_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-30To50_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-30to50_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-470To600_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-50To80_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-50to80_EMEnriched_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-600To800_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-800To1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-80To120_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
                # "QCD_Pt-80to120_EMEnriched_TuneCP5_13TeV-pythia8",
                "ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8",
                "ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8",
                "ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8",
                "ST_tW_antitop_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8",
                "ST_tW_top_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8",
                "TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8",
                "TTToHadronic_TuneCP5_13TeV-powheg-pythia8",
                "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8",
                "WW_TuneCP5_13TeV-pythia8",
                "WZ_TuneCP5_13TeV-pythia8",
                "ZZ_TuneCP5_13TeV-pythia8",
            ],
            "samples_exclude": [],
            "year": ["2018"]
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
    categories = {
        "baseline": [passthrough],
        "emu_pre": [emu_channel(parameters)],
        "ee_cr": [ee_channel(parameters), emu_veto(parameters), d0_cuts("ElectronGood", None, 50, "ElectronGood", None, 50)],
        "ee_sr": [ee_channel(parameters), emu_veto(parameters), d0_cuts("ElectronGood", 100, 10000, "ElectronGood", 100, 10000)],
        "emu_cr": [emu_channel(parameters), d0_cuts("ElectronGood", None, 50, "MuonGood", None, 50)],
        "emu_sr": [emu_channel(parameters), d0_cuts("ElectronGood", 100, 10000, "MuonGood", 100, 10000)],
        "mumu_cr": [mumu_channel(parameters), emu_veto(parameters), d0_cuts("MuonGood", None, 50, "MuonGood", None, 50)],
        "mumu_sr": [mumu_channel(parameters), emu_veto(parameters), d0_cuts("MuonGood", 100, 10000, "MuonGood", 100, 10000)],
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
