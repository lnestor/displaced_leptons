from configs.common import (
    DY_SUBSAMPLES,
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
from lib.categories import get_closure_test_cats
from lib.configurator import Configurator
from lib.cuts.generic import get_d0_gt, invert_cut
from lib.custom_fields import define_custom_nano_fields, define_DY_flavor
from lib.named_cut import NamedCut
from workflow import DisplacedLeptonProcessor

register_modules()
params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["Muon", *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "subsamples": DY_SUBSAMPLES,
        "priority": ["Muon", "DY", "Diboson", "SingleTop", "TTbar", "QCDEle", "QCDMu"],
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="Muon"),
    custom_fields = {
        "common": [define_custom_nano_fields],
        "bysample": {"DY": [define_DY_flavor]}
    },
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
        **get_closure_test_cats(
            channel="mumu",
            field="absd0_um",
            sweep_axis1_edges=[20, 30, 40, 50, 60, 70, 80, 90, 100],
            sweep_axis2_edges=[20, 100, 500],
            point_axis1_edges=[20, 30, 100],
            point_axis2_edges=[20, 100, 500]
        )
    },
    hists = {}
)
