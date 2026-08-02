from common import (
    DATA_SAMPLES,
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
register_modules()

from lib.custom_fields import (
    define_custom_nano_fields,
    define_gen_parent
)

from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)

from lib.named_cut import NamedCut
from lib.categories import get_default_cats, get_closure_test_cats
from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from hists import lepton_hists, background_hists

params = get_params()

default_cats = get_default_cats(channel="mumu")
closure_cats = get_closure_test_cats(channel="mumu")

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["Muon"],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024"]
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(),
    custom_fields = [
        define_custom_nano_fields,
        define_gen_parent
    ],
    object_selections = {
        "Electron": {"cuts": get_ele_cuts("ee")},
        "Muon": {"min": 2, "cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx")
    ],
    categories = {
        **default_cats,
        **closure_cats
    },
    hists = {
        **lepton_hists(coll="MuonGood", label="AllMuon", only_categories=["pcr"])
        **lepton_hists(coll="MuonGood", pos=0, label="LeadingMuon", only_categories=["pcr"])
        **lepton_hists(coll="MuonGood", pos=1, label="SubeadingMuon", only_categories=["pcr"])
    }
)
