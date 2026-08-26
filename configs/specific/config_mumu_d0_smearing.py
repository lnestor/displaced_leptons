from configs.common import (
    RUN_3_YEARS,
    get_default_skim_cuts,
    get_params,
    get_datasets,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
    get_supplements
)
from event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)
from lib.categories import get_pcr_cat
from lib.configurator import Configurator
from lib.cuts.generic import get_d0_gt, invert_cut
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
            "samples": ["Muon", "DY"],
            "year": RUN_3_YEARS
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(sample="Muon"),
    custom_fields = { "common": [define_custom_nano_fields] },
    object_selections = {
        "Electron": {"cuts": get_ele_cuts("emu")},
        "Muon": {"min": 2, "cuts": get_mu_cuts("mumu")}
    },
    event_preselections = [
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton delta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx"),
        NamedCut(cut=invert_cut(get_d0_gt("ElectronGood", 100)), label="emu veto")
    ],
    categories = get_pcr_cat(channel="mumu", field="absd0_um", threshold=PCR_THRESHOLD),
    hists = {
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
