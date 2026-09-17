from configs.common import (
    DY_SUBSAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    get_params,
    get_datasets,
    get_supplements,
    get_default_skim_cuts,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from lib.custom_fields import (
    define_custom_nano_fields,
    define_DY_flavor,
    define_gen_parent_values,
    define_gen_v0,
    define_selected_leptons,
    define_systemboost,
)
from lib.named_cut import NamedCut
from lib.categories import get_baseline_cat, get_closure_test_cats
from lib.cuts.generic import get_d0_gt, invert_cut
from event_selection import get_min_deltaR, get_no_in_material_vtx
from hists import correlation_hists, genvtx_hists, lepton_displacement_hists

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "subsamples": DY_SUBSAMPLES,
        "priority": ["EGamma", "DY", "TTbar", "Diboson"]
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="EGamma"),
    custom_fields = {
        "preselection": {
            "common": [define_custom_nano_fields, define_gen_parent_values, define_gen_v0],
            "bysample": {"DY": [define_DY_flavor]}
        },
        "postselection": {
            "common": [define_selected_leptons("ee"), define_systemboost("ee")]
        }
    },
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "no material vertices"),
        NamedCut(invert_cut(get_d0_gt("MuonGood", 100)), "emu veto")
    ],
    categories = {
        **get_baseline_cat(),
        **get_closure_test_cats(
            channel="ee",
            field="absd0_um",
            sweep_axis1_edges=[20, 30, 40, 50, 60, 70, 80, 90, 100],
            sweep_axis2_edges=[20, 100, 500],
            point_axis1_edges=[20, 30, 100],
            point_axis2_edges=[20, 100, 500]
        )
    },
    hists = {
        **genvtx_hists(only_categories=["baseline"]),
        **lepton_displacement_hists(coll="SelectedLeptons", label="AllElectron", only_categories=["baseline"]),
        **correlation_hists(channel="ee", only_categories=["baseline"]),
    }
)
