from configs.common import (
    MC_SAMPLES,
    RUN_3_YEARS,
    get_params,
    get_datasets,
    get_supplements,
    get_default_skim_cuts,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
)
register_modules()

from lib.workflow.analysis_processor import AnalysisProcessor
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_functions import get_nObj_min
from lib.categories import get_pcr_cat
from lib.cuts.generic import get_d0_gt, invert_cut
from hists import pcr_hists
from event_selection import get_min_deltaR, get_no_in_material_vtx

params = get_params()

PCR_THRESHOLD = 100

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "priority": ["EGamma", "DY", "TTbar", "Diboson"]
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
    categories = {
        "pcr": get_pcr_cat(channel="ee", field="absd0_um", threshold=PCR_THRESHOLD)["pcr"],
        "pcr_uncorrected": get_pcr_cat(channel="ee", field="absd0_um_original", threshold=PCR_THRESHOLD)["pcr"],
    },
    hists = {
        **pcr_hists(coll="ElectronGood", label="AllElectron", threshold=PCR_THRESHOLD),
        **pcr_hists(coll="ElectronGood", pos=0, label="LeadingElectron", threshold=PCR_THRESHOLD),
        **pcr_hists(coll="ElectronGood", pos=1, label="SubleadingElectron", threshold=PCR_THRESHOLD),
    }
)
