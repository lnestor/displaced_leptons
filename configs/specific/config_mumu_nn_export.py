from lib.configuration import (
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
from lib.custom_fields import define_custom_nano_fields
from lib.cuts.event_selection import (
    get_min_deltaR,
    get_min_muon_delta_t,
    get_n_back_to_back_muons,
    get_no_in_material_vtx
)
from lib.cuts.generic import get_d0_gt, invert_cut
from lib.named_cut import NamedCut
from lib.workflow.analysis_processor import AnalysisProcessor
from pocket_coffea.lib.cut_functions import get_nObj_min
from pocket_coffea.lib.columns_manager import ColOut

register_modules()
params = get_params()

LEP_COLS = ["pt", "eta", "phi", "charge", "absd0_um", "sabsd0", "dz", "sip3d", "customIso"]

COLS = [
    ColOut("MuonGood", LEP_COLS, flatten=False, pos_end=2),
    ColOut("PuppiMET", ["pt", "phi"]),
    ColOut("events", ["run", "luminosityBlock", "event"]),
]

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": MC_SAMPLES,
            "year": RUN_3_YEARS
        },
        "priority": ["DY", "Diboson", "SingleTop", "TTbar", "QCDEle", "QCDMu"]
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    workflow_options = {"dump_columns_as_arrays_per_chunk": "root://cmseos.fnal.gov//store/user/lnestor/nn_columns/staging/mumu/"},
    skim = get_default_skim_cuts(sample="Muon"),
    custom_fields = {"preselection": {"common": [define_custom_nano_fields]}},
    object_selections = {"Electron": get_ele_cuts("emu"), "Muon": get_mu_cuts("mumu")},
    event_preselections = [
        NamedCut(get_nObj_min(2, coll="MuonGood"), ">= 2 good muons"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton delta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx"),
        NamedCut(cut=invert_cut(get_d0_gt("ElectronGood", 100)), label="emu veto")
    ],
    categories = get_baseline_cat(),
    hists = {},
    columns = {"common": {"inclusive": COLS}})
