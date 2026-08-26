from configs.common import (
    RUN_3_YEARS,
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules
)
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)
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
            "samples": ["MuonEG", "TTbar"],
            "year": RUN_3_YEARS
        }
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
        NamedCut(cut=get_min_deltaR("ElectronGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="emu"), label="Material vtx")
    ],
    categories = get_pcr_cat(channel="emu", field="absd0_um", threshold=PCR_THRESHOLD),
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
        ]),
        "AllMuon_d0": HistConf([
            Axis(
                coll="MuonGood",
                field="d0_um",
                bins=2*PCR_THRESHOLD,
                start=-PCR_THRESHOLD,
                stop=PCR_THRESHOLD,
                label=rf"Muon $d_0$ [$\mu m$]"
            )
        ])
    },
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator], # No smear calibrator
)
