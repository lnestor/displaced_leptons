from configs.common import (
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
    get_ele_cuts,
    get_mu_cuts
)
from event_selection import get_min_deltaR, get_no_in_material_vtx
from lib.configurator import Configurator
from lib.cuts.generic import get_d0_gt, invert_cut
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
            "samples": ["EGamma"],
            "year": RUN_3_YEARS
        },
        "priority": ["EGamma"]
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    workflow_options = {"skim_mode": "presel_any_variation"},
    save_skimmed_files = "root://cmseos.fnal.gov//store/user/lnestor/skims/ee/",
    skim = get_default_skim_cuts(sample="EGamma"),
    custom_fields = {"common": [define_custom_nano_fields]},
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "material vertex"),
        NamedCut(invert_cut(get_d0_gt("MuonGood", 100)), "emu veto")
    ],
    categories = {},
    hists = {},
    # The calibrators either change pt or d0, none of which are being used in this config
    calibrators = []
)
