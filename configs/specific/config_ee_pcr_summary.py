from configs.common import (
    get_params,
    get_datasets,
    get_supplements,
    get_default_skim_cuts,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields
from lib.named_cut import NamedCut
from lib.categories import get_pcr_cat
from hists import pcr_hists
from event_selection import get_min_deltaR, get_no_in_material_vtx

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma", "DY", "TTbar", "Diboson", "SingleTop", "QCDEle", "QCDMu"],
            "year": ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]
        },
        "priority": ["EGamma", "DY", "TTbar", "Diboson"]
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
    categories = get_pcr_cat(channel="ee", field="absd0_um", threshold=50),
    hists = {
        **pcr_hists(coll="ElectronGood", label="AllElectron"),
        **pcr_hists(coll="ElectronGood", pos=0, label="LeadingElectron"),
        **pcr_hists(coll="ElectronGood", pos=1, label="SubleadingElectron"),
    }
)
