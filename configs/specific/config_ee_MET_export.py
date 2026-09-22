from configs.common import (
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
    get_ele_cuts
)
from event_selection import get_min_deltaR, get_no_in_material_vtx
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
            "samples": ["MET"],
            "year": RUN_3_YEARS
        }
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    workflow_options = {"skim_mode": "presel_any_variation"},
    save_skimmed_files = "root://cmseos.fnal.gov//store/user/lnestor/skims_staging/ee/",
    skim = get_default_skim_cuts(sample=["MET"]),
    custom_fields = {"preselection": {"common": [define_custom_nano_fields]}},
    object_selections = {
        # Specifically skipping pt cut for trigger efficiency measurement
        "Electron": get_ele_cuts("ee", skip_pt=True)
    },
    event_preselections = [
        NamedCut(get_nObj_min(2, coll="ElectronGood"), ">= 2 good electrons"),
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "material vertex")
        # Specifically skipping emu veto for trigger efficiency measurement
    ],
    categories = {},
    hists = {},
    # Isolation cut divides by pt, so we need pt calibrated; skip d0 calibration as d0 is unused here
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator]
)
