from configs.common import (
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules,
)
from event_selection import (
    get_min_deltaR,
    get_min_muon_delta_t,
    get_n_back_to_back_muons,
    get_no_in_material_vtx
)
from hists import pcr_hists
from lib.categories import get_pcr_cat
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from workflow import DisplacedLeptonProcessor

register_modules()
params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["MuonEG", "TTbar", "SingleTop", "Diboson", "DY", "QCDEle", "QCDMu"],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]
        },
        "priority": ["MuonEG", "TTbar", "SingleTop", "Diboson", "DY", "QCDEle", "QCDMu"]
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(),
    custom_fields = { "common": [define_custom_nano_fields] },
    object_selections = {
        "Electron": {"min": 1, "cuts": get_ele_cuts("emu")},
        "Muon": {"min": 1, "cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("ElectronGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="emu"), label="Material vtx")
    ],
    categories = get_pcr_cat(channel="emu", field="absd0_um", threshold=50),
    hists = {
        **pcr_hists(coll="ElectronGood", pos=0, label="LeadingElectron"),
        **pcr_hists(coll="ElectronGood", label="AllElectron"),
        **pcr_hists(coll="MuonGood", pos=0, label="LeadingMuon"),
        **pcr_hists(coll="MuonGood", label="AllMuon"),
    }
)
