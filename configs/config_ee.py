from lib.configuration import (
    DY_SUBSAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules,
)
from lib.categories import get_baseline_cat
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields, define_DY_flavor, define_gen_parent_values
from lib.cuts.event_selection import get_min_deltaR, get_no_in_material_vtx
from lib.cuts.generic import get_d0_gt, invert_cut
from lib.named_cut import NamedCut
from lib.workflow.analysis_processor import AnalysisProcessor
from pocket_coffea.lib.cut_functions import get_nObj_min

register_modules()
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
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    skim = get_default_skim_cuts(sample="EGamma"),
    custom_fields = {
        "preselection": {
            "common": [define_custom_nano_fields, define_gen_parent_values],
            "bysample": {"DY": [define_DY_flavor]}
        }
    },
    object_selections = {
        "Electron": get_ele_cuts("ee"),
        "Muon": get_mu_cuts("emu")
    },
    event_preselections = [
        NamedCut(get_nObj_min(2, coll="ElectronGood"), ">= 2 good electrons"),
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "no material vertices"),
        NamedCut(invert_cut(get_d0_gt("MuonGood", 100)), "emu veto")
    ],
    categories = get_baseline_cat(),
    hists = {}
)
