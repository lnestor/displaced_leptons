from pocket_coffea.lib.cut_functions import get_HLTsel, goldenJson, eventFlags
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from pocket_coffea.parameters import defaults

from lib.named_cut import NamedCut
from event_selection import get_d0_lt
from channel_selection import ee_cuts, mumu_cuts, emu_veto, emu_cuts

import glob
from pathlib import Path

RUN_2_YEARS = [
    "2016_postVFP",
    "2017",
    "2018"
]

RUN_3_YEARS = [
    "2022_preEE",
    "2022_postEE",
    "2023_preBPix",
    "2023_postBPix",
    "2024",
    "2025"
]

DATA_SAMPLES = [
    "MuonEG",
    "Muon",
    "EGamma",
    "DoubleMuon",
]

MC_SAMPLES = [
    "DY",
    "TTbar",
    "SingleTop",
    "Diboson",
    "QCD_Ele",
    "QCD_Mu"
]

DEFAULT_WEIGHTS = {
    "common": {
        "inclusive": [
            "genWeight",
            "lumi",
            "XS"
        ],
        "bycategory": {}
    },
    "bysample": {}
}

DEFAULT_VARIATIONS = {
    "weights": {
        "common": {
            "inclusive": [],
            "bycategory": {}
        },
        "bysamples": {}
    }
}

DEFAULT_CALIBRATORS = [ElectronsScaleCalibrator, MuonsCalibrator]

DEFAULT_SKIM_CUTS = [
    NamedCut(cut=eventFlags, label="MET Filters"),
    NamedCut(cut=goldenJson, label="Golden JSON"),
    NamedCut(cut=get_HLTsel(), label="Passes triggers")
]

def get_channel_categories(params, include_pcr=False, add_veto=True):
    cats = { "baseline": [passthrough] }

    if add_veto:
        cats["ee"] = [*ee_cuts(params), emu_veto(params)]
        cats["emu"] = [*emu_cuts(params)]
        cats["mumu"] = [*mumu_cuts(params), emu_veto(params)]
    else:
        cats["ee"] = [*ee_cuts(params)]
        cats["emu"] = [*emu_cuts(params)]
        cats["mumu"] = [*mumu_cuts(params)]

    if include_pcr:
        # Deliberately always adding the veto to the PCR, can modify if needed
        cats["ee_pcr"] = [*ee_cuts(params), emu_veto(params), get_d0_lt("ElectronGood_ee", 50, 0), get_d0_lt("ElectronGood_ee", 50, 1)],
        cats["emu_pcr"] = [*emu_cuts(params), get_d0_lt("ElectronGood_emu", 50, 0), get_d0_lt("MuonGood_emu", 50, 0)],
        cats["mumu_pcr"] = [*mumu_cuts(params), emu_veto(params), get_d0_lt("MuonGood_mumu", 50, 0), get_d0_lt("MuonGood_mumu", 50, 1)],

    return cats


def register_modules():
    import cloudpickle
    import workflow
    import event_selection
    import object_selection
    import hists
    import channel_selection
    import lib
    import lib.named_cut as named_cut
    import lib.object_cutflow as object_cutflow
    import common as configs_common
    cloudpickle.register_pickle_by_value(workflow)
    cloudpickle.register_pickle_by_value(event_selection)
    cloudpickle.register_pickle_by_value(object_selection)
    cloudpickle.register_pickle_by_value(hists)
    cloudpickle.register_pickle_by_value(channel_selection)
    cloudpickle.register_pickle_by_value(lib)
    cloudpickle.register_pickle_by_value(named_cut)
    cloudpickle.register_pickle_by_value(object_cutflow)
    cloudpickle.register_pickle_by_value(configs_common)


def get_params():
    localdir = str(Path(__file__).parent.parent)
    path = f"{localdir}/params"

    default_parameters = defaults.get_default_parameters()
    defaults.register_configuration_dir("config_dir", path)

    parameters = defaults.merge_parameters_from_files(
        default_parameters,
        f"{path}/object_preselection.yaml",
        f"{path}/triggers.yaml",
        f"{path}/plotting.yaml",
        f"{path}/categories.yaml",
        update=True
    )

    return parameters


def get_datasets(subdir):
    localdir = str(Path(__file__).parent.parent)
    return [f for f in glob.glob(f"{localdir}/datasets/{subdir}/*.json")]
