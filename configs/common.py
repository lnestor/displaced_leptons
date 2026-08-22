from pocket_coffea.lib.cut_functions import get_HLTsel, goldenJson, eventFlags
from pocket_coffea.parameters import defaults

from lib.named_cut import NamedCut
from event_selection import get_DY_flavor
from lib.cuts.generic import get_d0_lt, get_d0_gt
from object_selection import (
    get_min_pt,
    get_max_eta,
    get_sc_gap_veto,
    get_ele_tight_id,
    get_ele_tight_id_single_bit,
    get_max_iso,
    get_etaphi_veto,
    get_muon_tight_id,
)

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

DY_SUBSAMPLES = {
    "DY": {
        "ee": [get_DY_flavor(11)],
        "mumu": [get_DY_flavor(13)],
        "tautau": [get_DY_flavor(15)],
    }
}


def get_default_skim_cuts(sample=None):
    cuts = [
        NamedCut(cut=eventFlags, label="MET Filters"),
        NamedCut(cut=goldenJson, label="Golden JSON"),
    ]

    if sample is None:
        cuts.append(NamedCut(cut=get_HLTsel(), label="Passes triggers"))
    else:
        cuts.append(NamedCut(cut=get_HLTsel(primaryDatasets=[sample]), label="Passes triggers"))

    return cuts


def get_ele_cuts(channel, skip_pt=False, split_id=False):
    cuts = [
        NamedCut(get_max_eta("Electron", channel=channel), r"$>={count}$ e with $|\eta|<{val}$"),
        NamedCut(get_sc_gap_veto("Electron"), r"$>={count} e not in supercluster gap"),
        NamedCut(get_etaphi_veto("Electron", channel=channel), r"$>={count}$ e passing $\eta-\phi$ veto"),
        NamedCut(get_min_pt("Electron", channel=channel), r"$>={count}$ e with $p_T>{val}$ GeV") if not skip_pt else None,
    ]

    if split_id:
        cuts.extend([
            NamedCut(get_ele_tight_id_single_bit("Electron", 4), r"$>={count}$ e passing full5x5 $\sigma_{i\eta i\eta}$ cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 2), r"$>={count}$ e passing $|\delta\eta_{seed}|$ cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 3), r"$>={count}$ e passing $|\delta\phi_{in}|$ cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 5), r"$>={count}$ e passing H/E cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 6), r"$>={count}$ e passing $|1/E - 1/p|$ cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 9), r"$>={count}$ e passing missing inner hits cut"),
            NamedCut(get_ele_tight_id_single_bit("Electron", 8), r"$>={count}$ e passing conversion veto"),
        ])
    else:
        cuts.append(NamedCut(get_ele_tight_id("Electron"), r"$>={count}$ e passing tight ID (minus isolation requirement)"))

    cuts.append(NamedCut(get_max_iso("Electron", channel=channel), r"$>={count}$ e passing tight custom isolation"))
    return [cut for cut in cuts if cut is not None]


def get_mu_cuts(channel, skip_pt=False):
    cuts = [
        NamedCut(get_max_eta("Muon", channel=channel), r"$>={count}$ $\mu$ with $|\eta|<{val}$"),
        NamedCut(get_etaphi_veto("Muon", channel=channel), r"$>={count}$ $\mu$ passing $\eta-\phi$ veto"),
        NamedCut(get_min_pt("Muon", channel=channel), r"$>={count}$ $\mu$ with $p_T>{val}$ GeV") if not skip_pt else None,
        NamedCut(get_muon_tight_id("Muon"), r"$>={count}$ $\mu$ passing tight ID"),
        NamedCut(get_max_iso("Muon", channel=channel), r"$>={count}$ $\mu$ passing tight custom isolation"),
    ]
    return [cut for cut in cuts if cut is not None]


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
    import lib.categories as categories
    import configs.common as configs_common
    cloudpickle.register_pickle_by_value(workflow)
    cloudpickle.register_pickle_by_value(event_selection)
    cloudpickle.register_pickle_by_value(object_selection)
    cloudpickle.register_pickle_by_value(hists)
    cloudpickle.register_pickle_by_value(channel_selection)
    cloudpickle.register_pickle_by_value(lib)
    cloudpickle.register_pickle_by_value(named_cut)
    cloudpickle.register_pickle_by_value(object_cutflow)
    cloudpickle.register_pickle_by_value(categories)
    cloudpickle.register_pickle_by_value(configs_common)


def get_params():
    localdir = str(Path(__file__).parent.parent)
    path = f"{localdir}/params"

    default_parameters = defaults.get_default_parameters()
    defaults.register_configuration_dir("config_dir", path)

    parameters = defaults.merge_parameters_from_files(
        default_parameters,
        f"{path}/object_selection.yaml",
        f"{path}/regions.yaml",
        f"{path}/triggers.yaml",
        f"{path}/d0_smearing.yaml",
        update=True
    )

    return parameters


def get_datasets(subdir):
    localdir = str(Path(__file__).parent.parent)
    return [f for f in glob.glob(f"{localdir}/datasets/{subdir}/*.json")]


def get_supplements():
    localdir = str(Path(__file__).parent.parent)
    return [f for f in glob.glob(f"{localdir}/datasets/supplements/*.json")]
