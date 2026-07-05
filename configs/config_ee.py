from common import (
    DATA_SAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    DEFAULT_SKIM_CUTS,
    get_params,
    get_datasets,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
    get_default_categories,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields, define_gen_parent
from hists import lepton_hists
from event_selection import get_min_deltaR, get_no_in_material_vtx

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            # "samples": ["MuonEG", *MC_SAMPLES],
            "samples": ["EGamma"],
            "samples_exclude": [],
            # "year": RUN_3_YEARS
            "year": ["2022_preEE"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    skim = DEFAULT_SKIM_CUTS,
    custom_fields = [
        define_custom_nano_fields,
        define_gen_parent
    ],
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        get_min_deltaR("ElectronGood", "ElectronGood", 0.2),
        get_no_in_material_vtx(channel="ee")
    ],
    categories = get_default_categories(channel="ee"),
    hists = {
        **lepton_hists(coll="ElectronGood", label="Electron"),
        **lepton_hists(coll="ElectronGood", pos=0, label="LeadingElectron"),
        **lepton_hists(coll="ElectronGood", pos=1, label="SubleadingElectron"),
    }
)
