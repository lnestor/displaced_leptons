from common import (
    DATA_SAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    DEFAULT_WEIGHTS,
    DEFAULT_VARIATIONS,
    DEFAULT_CALIBRATORS,
    DEFAULT_SKIM_CUTS,
    get_channel_categories,
    get_params,
    get_datasets,
    register_modules,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from lib.configuator import Configurator
from hists import lepton_hists, background_hists

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["MuonEG", *MC_SAMPLES],
            "samples_exclude": [],
            "year": RUN_3_YEARS
        }
    },
    workflow = DisplacedLeptonProcessor,
    skim = DEFAULT_SKIM_CUTS,
    object_selections = {
        "Electron": {
            "min": 2,
            "cuts": [
            ]
        },
        "Muon": {
            "cuts": [
            ]
        }

    },
    event_preselections = [
        NamedCut(cut=get_nElectrons(2), label="")
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_dilepton_deltaR("emu", 0.2), label=""),
        NamedCut(cut=get_no_in_material_vtx(MUON_FLAVOR, ELECTRON_FLAVOR), label="")
    ],
    categories = get_default_categories(coll1="ElectronGood", coll2="MuonGood", pt_coll="MuonGood", pt_threshold=50)
    variables = {
        **lepton_hists(coll="ElectronGood", label="Electron"),
    },
    calibrators = DEFAULT_CALIBRATORS,
    weights = DEFAULT_WEIGHTS,
    variations = DEFAULT_VARIATIONS,
)
