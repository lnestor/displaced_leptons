from configs.common import (
    MC_SAMPLES,
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
    get_ele_cuts,
    get_mu_cuts,
)
from event_selection import (
    get_min_deltaR,
    get_min_muon_delta_t,
    get_n_back_to_back_muons,
    get_no_in_material_vtx
)
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_functions import get_nObj_min
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from lib.workflow.analysis_processor import AnalysisProcessor


register_modules()
params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": MC_SAMPLES,
            "year": RUN_3_YEARS
        },
        "priority": ["TTbar", "SingleTop", "Diboson", "DY", "QCDEle", "QCDMu"]
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    workflow_options = {"skim_mode": "presel_any_variation"},
    save_skimmed_files = "root://cmseos.fnal.gov//store/user/lnestor/skims_staging/emu/",
    skim = get_default_skim_cuts(sample=["MuonEG", "MET"]),
    custom_fields = {"preselection": {"common": [define_custom_nano_fields]}},
    object_selections = {
        # Specifically skipping pt cut for trigger efficiency measurement
        "Electron": get_ele_cuts("emu", skip_pt=True),
        "Muon": get_mu_cuts("emu", skip_pt=True)
    },
    event_preselections = [
        NamedCut(get_nObj_min(1, coll="ElectronGood"), ">= 1 good electrons"),
        NamedCut(get_nObj_min(1, coll="MuonGood"), ">= 1 good muons"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("ElectronGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="emu"), label="Material vtx")
    ],
    categories = {},
    hists = {},
    # Isolation cut divides by pt, so we need pt calibrated; skip d0 calibration as d0 is unused here
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator]
)
