from common import (
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
    get_mu_cuts,
    MC_SAMPLES
)

register_modules()

from lib.named_cut import NamedCut
from pocket_coffea.parameters.cuts import passthrough
from lib.custom_fields import define_custom_nano_fields
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx,
    get_min_n_pt
)
from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from pocket_coffea.parameters.histograms import HistConf, Axis
from pocket_coffea.lib.cut_functions import get_HLTsel_custom

ALL_TRIGGERS = [
    "HLT_DoubleMu43NoFiltersNoVtx",
    "HLT_DoubleMu48NoFiltersNoVtx",
    "HLT_DoubleL3Mu16_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3Mu18_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3Mu20_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3dTksMu16_10NoVtx_DxyMin0p01cm",
]

TARGET_TRIGGERS = [
    "HLT_DoubleMu43NoFiltersNoVtx",
]

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["Muon", *MC_SAMPLES],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024"]
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="MET"),
    custom_fields = {
        "common": [define_custom_nano_fields]
    },
    object_selections = {
        "Muon": {"min": 2, "cuts": get_mu_cuts("mumu", skip_pt=True)}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon pairs with timing consistent with cosmics"),
        NamedCut(get_min_deltaR("MuonGood", "MuonGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="mumu"), "material vertex")
    ],
    categories = {
        "baseline": [passthrough],
        **{f"passes_{trigger}": [get_HLTsel_custom([trigger])] for trigger in ALL_TRIGGERS},
        "passes_OR": [get_HLTsel_custom(TARGET_TRIGGERS)],
        "passes_OR_plateau": [
            get_HLTsel_custom(TARGET_TRIGGERS),
            NamedCut(get_min_n_pt("mumu"), r">=2 $\mu$ with $p_T$ above plateau threshold")
        ]
    },
    hists = {
        "AllMuon_pt": HistConf([Axis(coll="MuonGood", field="pt", bins=100, start=0, stop=500, label=rf"Muon $p_T$ [GeV]")], exclude_categories=["passes_OR_plateau"]),
        "LeadingMuon_pt": HistConf([Axis(coll="MuonGood", pos=0, field="pt", bins=100, start=0, stop=500, label=rf"Leading muon $p_T$ [GeV]")], exclude_categories=["passes_OR_plateau"]),
        "SubleadingMuon_pt": HistConf([Axis(coll="MuonGood", pos=1, field="pt", bins=100, start=0, stop=500, label=rf"Subleading muon $p_T$ [GeV]")], exclude_categories=["passes_OR_plateau"]),
        "AllMuon_d0": HistConf([Axis(coll="MuonGood", field="absd0_um", bins=100, start=0, stop=1000, label=rf"Muon $d_0$ [$\mu m$]")], exclude_categories=["passes_OR_plateau"]),
        "LeadingMuon_d0": HistConf([Axis(coll="MuonGood", pos=0, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Leading muon $d_0$ [$\mu m$]")], exclude_categories=["passes_OR_plateau"]),
        "SubleadingMuon_d0": HistConf([Axis(coll="MuonGood", pos=1, field="absd0_um", bins=100, start=0, stop=1000, label=rf"Subleading muon $d_0$ [$\mu m$]")], exclude_categories=["passes_OR_plateau"]),
    },
)
