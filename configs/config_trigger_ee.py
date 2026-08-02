from common import (
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_ele_cuts
)

register_modules()

from lib.named_cut import NamedCut
from lib.categories import get_default_categories
from pocket_coffea.parameters.cuts import passthrough
from lib.custom_fields import define_custom_nano_fields
from event_selection import get_min_deltaR, get_no_in_material_vtx
from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from pocket_coffea.parameters.histograms import HistConf, Axis
from pocket_coffea.lib.cut_functions import get_HLTsel_custom
from hists import lepton_hists

TRIGGERS = [
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

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma"],
            "year": ["2024"]
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="MET"),
    custom_fields = [
        define_custom_nano_fields
    ],
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee", skip_pt=True, split_id=True)}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "material vertex")
    ],
    categories = {
        "baseline": [passthrough],
        **{f"passes_{trigger}": [get_HLTsel_custom([trigger])] for trigger in TRIGGERS},
        "passes_OR": [get_HLTsel_custom(["HLT_DoublePhoton70", "HLT_Diphoton30_22_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"])]
    },
    hists = {
        "AllElectron_pt": HistConf([Axis(coll="ElectronGood", field="pt", bins=100, start=0, stop=500, label=rf"Leading electron $p_T$ [GeV]")]),
        "LeadingElectron_pt": HistConf([Axis(coll="ElectronGood", pos=0, field="pt", bins=100, start=0, stop=500, label=rf"Leading electron $p_T$ [GeV]")]),
        "SubleadingElectron_pt": HistConf([Axis(coll="ElectronGood", pos=1, field="pt", bins=100, start=0, stop=500, label=rf"Subleading electron $p_T$ [GeV]")]),
        "AllElectron_d0": HistConf([Axis(coll="ElectronGood", field="absd0_um", bins=100, start=0, stop=1000, label=rf"Leading electron $d_0$ [$\mu m$]")]),
        "LeadingElectron_d0": HistConf([Axis(coll="ElectronGood", pos=0, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Leading electron $d_0$ [$\mu m$]")]),
        "SubleadingElectron_d0": HistConf([Axis(coll="ElectronGood", pos=1, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Subleading electron $d_0$ [$\mu m$]")]),
    },
)
