from configs.common import (
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
from event_selection import (
    get_min_deltaR,
    get_min_muon_delta_t,
    get_n_back_to_back_muons,
    get_no_in_material_vtx
)
from lib.categories import get_closure_test_cats
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
            "samples": ["MuonEG", *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "priority": ["MuonEG", "TTbar", "SingleTop", "Diboson", "DY", "QCDEle", "QCDMu"]
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="MuonEG"),
    custom_fields = {"common": [define_custom_nano_fields]},
    object_selections = {
        "Electron": {"min": 1, "cuts": get_ele_cuts("emu")},
        "Muon": {"min": 1, "cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("ElectronGood", "MuonGood", 0.2), label="Dilepton delta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="emu"), label="Material vtx")
    ],
    categories = {
        **get_closure_test_cats(
            channel="emu",
            field="absd0_um",
            sweep_axis1_edges=[20, 30, 40, 50, 60, 70, 80, 90, 100],
            sweep_axis2_edges=[20, 100, 500],
            point_axis1_edges=[20, 30, 100],
            point_axis2_edges=[20, 100, 500]
        )
    },
    hists = {}
)
