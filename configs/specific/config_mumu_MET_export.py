from configs.common import (
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    register_modules,
    get_datasets,
    get_supplements,
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
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from workflow import DisplacedLeptonProcessor


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
    workflow = DisplacedLeptonProcessor,
    workflow_options = {"skim_mode": "presel_any_variation"},
    save_skimmed_files = "root://cmseos.fnal.gov//store/user/lnestor/skims_staging/mumu/",
    skim = get_default_skim_cuts(sample=["MET"]),
    custom_fields = {"common": [define_custom_nano_fields]},
    object_selections = {
        # Specifically skipping pt cut for trigger efficiency measurement
        "Muon": {"min": 2, "cuts": get_mu_cuts("mumu", skip_pt=True)}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx")
        # Specifically skipping emu veto for trigger efficiency measurement
    ],
    categories = {},
    hists = {},
    # Isolation cut divides by pt, so we need pt calibrated; skip d0 calibration as d0 is unused here
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator]
)
