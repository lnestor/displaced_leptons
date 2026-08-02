from common import (
    DATA_SAMPLES,
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
from lib.custom_fields import define_custom_nano_fields, define_gen_parent
from lib.named_cut import NamedCut
from lib.categories import get_default_cats, get_closure_test_cats
from hists import lepton_hists
from pocket_coffea.parameters.histograms import HistConf, Axis
from event_selection import get_min_deltaR, get_no_in_material_vtx

params = get_params()

default_cats = get_default_cats(channel="ee")
closure_cats = get_closure_test_cats(channel="ee")

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma"],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix"]
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
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "no material vertices")
    ],
    categories = {
        # **default_cats,
        **closure_cats
    },
    hists = {
        **lepton_hists(coll="ElectronGood", label="Electron", only_categories=["pcr"]),
        **lepton_hists(coll="ElectronGood", pos=0, label="LeadingElectron", only_categories=["pcr"]),
        **lepton_hists(coll="ElectronGood", pos=1, label="SubleadingElectron", only_categories=["pcr"]),
    }
)
