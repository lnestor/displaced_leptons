from configs.common import (
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules
)
from event_selection import get_min_deltaR, get_no_in_material_vtx
from lib.categories import get_pcr_cat
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from pocket_coffea.parameters.histograms import HistConf, Axis
from workflow import DisplacedLeptonProcessor

register_modules()
params = get_params()

PCR_THRESHOLD = 80

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", "DY"],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="EGamma"),
    custom_fields = {"common": [define_custom_nano_fields]},
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        NamedCut(get_no_in_material_vtx(channel="ee"), "no material vertices")
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
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator], # No smear calibrator
)
