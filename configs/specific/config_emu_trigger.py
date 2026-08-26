from pocket_coffea.lib.cut_functions import get_HLTsel_custom
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.parameters.histograms import HistConf, Axis

from common import (
    MC_SAMPLES,
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
    get_ele_cuts,
    get_mu_cuts
)
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from workflow import DisplacedLeptonProcessor

ALL_TRIGGERS = [
    "HLT_Mu43NoFiltersNoVtx_Photon43_CaloIdL",
    "HLT_Mu43NoFiltersNoVtxDisplaced_Photon43_CaloIdL",
    "HLT_Mu38NoFiltersNoVtxDisplaced_Photon38_CaloIdL",
    "HLT_Mu20NoFiltersNoVtxDisplaced_Photon20_CaloCustomId",
    "HLT_Mu48NoFiltersNoVtx_Photon48_CaloIdL",
]

TARGET_TRIGGERS = [
    "HLT_Mu48NoFiltersNoVtx_Photon48_CaloIdL",
]

register_modules()
params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["MuonEG", *MC_SAMPLES],
            "year": RUN_3_YEARS,
        },
        "priority": ["MuonEG", "TTbar", "SingleTop", "Diboson", "DY"]
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="MET"),
    custom_fields = { "common": [define_custom_nano_fields] },
    object_selections = {
        "Electron": {"min": 1, "cuts": get_ele_cuts("emu", skip_pt=True)},
        "Muon": {"min": 1, "cuts": get_mu_cuts("emu", skip_pt=True)}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon pairs with timing consistent with cosmics"),
        NamedCut(get_min_deltaR("ElectronGood", "MuonGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="emu"), "material vertex")
    ],
    categories = {
        "baseline": [passthrough],
        **{f"passes_{trigger}": [get_HLTsel_custom([trigger])] for trigger in ALL_TRIGGERS},
        "passes_target_OR": [get_HLTsel_custom(TARGET_TRIGGERS)]
    },
    hists = {
        "LeadingElectron_pt": HistConf([Axis(coll="ElectronGood", pos=0, field="pt", bins=200, start=0, stop=400, label=rf"Leading electron $p_T$ [GeV]")]),
        "LeadingElectron_d0": HistConf([Axis(coll="ElectronGood", pos=0, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Leading electron $d_0$ [$\mu m$]")]),
        "LeadingMuon_pt": HistConf([Axis(coll="MuonGood", pos=0, field="pt", bins=200, start=0, stop=400, label=rf"Leading muon $p_T$ [GeV]")]),
        "LeadingMuon_d0": HistConf([Axis(coll="MuonGood", pos=0, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Leading muon $d_0$ [$\mu m$]")]),
    },
)
