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


def get_default_categories(coll1, coll2, pt_coll, pt_threshold):
    return {
        "baseline": [passthrough]
        "pcr": [get_d0_lt(coll1, 50, 0), get_d0_lt(coll2, 50, 0)],
        "a": [get_d0_lt(coll1, 100, 0), get_d0_lt(coll2, 100, 0)],
        "b": [get_d0_gt(coll1, 100, 0), get_d0_lt(coll2, 100, 0)],
        "b_lowd0_lowpt": [get_d0_between(coll1, 100, 500, 0), get_d0_lt(coll2, 100, 0), get_pt_lt(pt_coll, pt_threshold, 0)],
        "b_lowd0_highpt": [get_d0_between(coll1, 100, 500, 0), get_d0_lt(coll2, 100, 0), get_pt_gt(pt_coll, pt_threshold, 0)],
        "b_highd0": [get_d0_gt(coll1, 500, 0), get_d0_lt(coll2, 100, 0)],
        "c": [get_d0_lt(coll1, 100, 0), get_d0_gt(coll2, 100, 0)],
        "c_lowd0_lowpt": [get_d0_lt(coll1, 100, 0), get_d0_between(coll2, 100, 500, 0), get_pt_lt(pt_coll, pt_threshold, 0)],
        "c_lowd0_highpt": [get_d0_lt(coll1, 100, 0), get_d0_between(coll2, 100, 500, 0), get_pt_gt(pt_coll, pt_threshold, 0)],
        "c_highd0": [get_d0_lt(coll1, 500, 0), get_d0_gt(coll2, 100, 0)],
        "sr1_lowpt": [get_d0_between(coll1, 100, 500, 0), get_d0_between(coll2, 100, 500, 0), get_pt_lt(pt_coll, pt_threshold, 0)],
        "sr1_highpt": [get_d0_between(coll1, 100, 500, 0), get_d0_between(coll2, 100, 500, 0), get_pt_gt(pt_coll, pt_threshold, 0)],
        "sr2": [get_d0_gt(coll1, 500, 0), get_d0_between(coll2, 100, 500, 0)],
        "sr3": [get_d0_between(coll1, 100, 500, 0), get_d0_gt(coll2, 500, 0)],
        "sr4": [get_d0_gt(coll1, 500, 0), get_d0_g5(coll2, 500, 0)],
    }

def get_channel_categories(params, include_pcr=False, skip_pt=False, add_veto=True):
    cats = { "baseline": [passthrough] }

    if add_veto:
        cats["ee"] = [*ee_cuts(params, skip_pt=skip_pt), emu_veto(params, skip_pt=skip_pt)]
        cats["emu"] = [*emu_cuts(params, skip_pt=skip_pt)]
        cats["mumu"] = [*mumu_cuts(params, skip_pt=skip_pt), emu_veto(params, skip_pt=skip_pt)]
    else:
        cats["ee"] = [*ee_cuts(params, skip_pt=skip_pt)]
        cats["emu"] = [*emu_cuts(params, skip_pt=skip_pt)]
        cats["mumu"] = [*mumu_cuts(params, skip_pt=skip_pt)]

    if include_pcr:
        # Deliberately always adding the veto to the PCR, can modify if needed
        cats["ee_pcr"] = [*ee_cuts(params), emu_veto(params), get_d0_lt("ElectronGood", 50, 0), get_d0_lt("ElectronGood", 50, 1)],
        cats["emu_pcr"] = [*emu_cuts(params), get_d0_lt("ElectronGood", 50, 0), get_d0_lt("MuonGood", 50, 0)],
        cats["mumu_pcr"] = [*mumu_cuts(params), emu_veto(params), get_d0_lt("MuonGood", 50, 0), get_d0_lt("MuonGood", 50, 1)],

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
