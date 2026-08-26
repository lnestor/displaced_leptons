from configs.common import (
    MC_SAMPLES,
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    get_datasets,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
    get_supplements
)
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)
from hists import pcr_hists
from lib.categories import get_pcr_cat
from lib.configurator import Configurator
from lib.cuts.generic import get_d0_gt, invert_cut
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from pocket_coffea.parameters.cuts import passthrough
from workflow import DisplacedLeptonProcessor

register_modules()
params = get_params()

PCR_THRESHOLD = 100

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["Muon", *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "priority": ["Muon", "DY", "Diboson", "SingleTop", "TTbar", "QCDEle", "QCDMu"],
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="Muon"),
    custom_fields = {"common": [define_custom_nano_fields]},
    object_selections = {
        "Electron": {"cuts": get_ele_cuts("emu")},
        "Muon": {"min": 2, "cuts": get_mu_cuts("mumu")}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx"),
        NamedCut(cut=invert_cut(get_d0_gt("ElectronGood", 100)), label="emu veto")
    ],
    categories = {
        **get_pcr_cat(channel="mumu", field="absd0_um", threshold=PCR_THRESHOLD)
    },
    hists = {
        **pcr_hists(coll="MuonGood", pos=0, label="LeadingMuon", threshold=PCR_THRESHOLD),
        **pcr_hists(coll="MuonGood", pos=1, label="SubleadingMuon", threshold=PCR_THRESHOLD),
        **pcr_hists(coll="MuonGood", label="AllMuon", threshold=PCR_THRESHOLD),
    }
)
