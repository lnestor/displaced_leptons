from common import (
    DEFAULT_WEIGHTS,
    DEFAULT_VARIATIONS,
    DEFAULT_CALIBRATORS,
    DEFAULT_SKIM_CUTS,
    get_channel_categories,
    get_params,
    register_modules,
    get_datasets
)

register_modules()

from workflow import DisplacedLeptonProcessor
from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.parameters.histograms import HistConf, Axis
from pocket_coffea.lib.cut_functions import get_HLTsel_custom
from hists import lepton_hists

params = get_params()
base_cats = get_channel_categories(params)

EE_TRIGGERS = [
    "HLT_DoublePhoton70",
    "HLT_DoublePhoton85",
    "HLT_DiEle27_WPTightCaloOnly_L1DoubleEG",
    "HLT_Diphoton30_22_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90",
    "HLT_Diphoton30_22_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass95",
    "HLT_Diphoton30_18_R9IdL_AND_HE_AND_IsoCaloId",
    "HLT_Diphoton30_18_R9IdL_AND_HE_AND_IsoCaloId_Mass55",
    "HLT_Diphoton24_14_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_Diphoton24_16_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_Diphoton22_14_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_DiphotonMVA14p25_Mass90",
    "HLT_DiphotonMVA14p25_Tight_Mass90"
]

def add_trigger_cats(channel_name, base_cuts, triggers):
    cats = {}
    for trigger in triggers:
        cats[f"{channel_name}_{trigger}"] = [*base_cuts, get_HLTsel_custom(trigger)]
    return cats

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["MET"],
            "samples_exclude": [],
            "year": ["2024"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    workflow_options = { "skip_pt_cut": True },
    skim = DEFAULT_SKIM_CUTS,
    categories = {
        **base_cats,
        **add_trigger_cats("ee", base_cats["ee"], EE_TRIGGERS)
    },
    variables = {
        **lepton_hists("ElectronGood", label="Electron"),
        **lepton_hists("MuonGood", label="Muon"),
    },
    preselections = [],
    calibrators = DEFAULT_CALIBRATORS,
    weights = DEFAULT_WEIGHTS,
    variations = DEFAULT_VARIATIONS,
)
