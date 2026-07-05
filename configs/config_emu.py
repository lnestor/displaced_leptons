from common import (
    DATA_SAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    DEFAULT_SKIM_CUTS,
    get_default_categories,
    get_params,
    get_datasets,
    register_modules,
    get_ele_cuts,
    get_mu_cuts
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
from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from hists import lepton_hists, background_hists

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("cmssw"),
        "filter": {
            "samples": ["MuonEG", *MC_SAMPLES],
            "samples_exclude": [],
            "year": ["2018"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    skim = DEFAULT_SKIM_CUTS,
    custom_fields = [
        define_custom_nano_fields,
        define_gen_parent
    ],
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
    categories = get_default_categories(channel="emu"),
    hists = {
        **lepton_hists(coll="ElectronGood", pos=0, label="LeadingElectron"),
        **lepton_hists(coll="MuonGood", pos=0, label="LeadingMuon"),
    }
)
