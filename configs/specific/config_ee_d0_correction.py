from lib.configuration import (
    RUN_3_YEARS,
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules
)
from lib.cuts.event_selection import get_min_deltaR, get_no_in_material_vtx
from lib.cuts.generic import get_d0_gt, invert_cut
from lib.categories import get_pcr_cat
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_functions import get_nObj_min
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from pocket_coffea.parameters.histograms import HistConf, Axis
from lib.workflow.analysis_processor import AnalysisProcessor

register_modules()
params = get_params()

PCR_THRESHOLD = 80

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", "DY"],
            "year": RUN_3_YEARS
        }
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    skim = get_default_skim_cuts(sample="EGamma"),
    custom_fields = {"preselection": {"common": [define_custom_nano_fields]}},
    object_selections = {
        "Electron": get_ele_cuts("ee"),
        "Muon": get_mu_cuts("emu")
    },
    event_preselections = [
        NamedCut(get_nObj_min(2, coll="ElectronGood"), ">= 2 good electrons"),
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "no material vertices"),
        NamedCut(invert_cut(get_d0_gt("MuonGood", 100)), "emu veto")
    ],
    categories = get_pcr_cat(channel="ee", field="absd0_um", threshold=PCR_THRESHOLD),
    hists = {
        "AllElectron_d0": HistConf([
            Axis(
                coll="ElectronGood",
                field="d0_um",
                bins=2*PCR_THRESHOLD,
                start=-PCR_THRESHOLD,
                stop=PCR_THRESHOLD,
                label=rf"Electron $d_0$ [$\mu m$]"
            )
        ])
    },
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator], # No correction calibrator
)
