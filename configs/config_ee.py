from common import (
    DATA_SAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    get_params,
    get_datasets,
    get_supplements,
    get_default_skim_cuts,
    register_modules,
    get_ele_cuts,
    get_mu_cuts,
    get_default_categories,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields, define_gen_parent
from lib.named_cut import NamedCut
from hists import lepton_hists
from pocket_coffea.parameters.histograms import HistConf, Axis
from event_selection import get_min_deltaR, get_no_in_material_vtx

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["EGamma"],
            "year": ["2024"]
        }
    },
    supplements = get_supplements(),
    workflow = DisplacedLeptonProcessor,
    skim = get_default_skim_cuts(),
    custom_fields = [
        define_custom_nano_fields,
        define_gen_parent
    ],
    object_selections = {
        "Electron": {"min": 2, "cuts": get_ele_cuts("ee")},
        "Muon": {"cuts": get_mu_cuts("emu")}
    },
    event_preselections = [
        NamedCut(get_min_deltaR("ElectronGood", "ElectronGood", 0.2), "min deltaR"),
        # get_no_in_material_vtx(channel="ee")
    ],
    categories = get_default_categories(channel="ee"),
    hists = {
        **lepton_hists(coll="ElectronGood", label="Electron"),
        **lepton_hists(coll="ElectronGood", pos=0, label="LeadingElectron"),
        **lepton_hists(coll="ElectronGood", pos=1, label="SubleadingElectron"),
        "d0_vs_phi": HistConf(
            [
                Axis(coll="ElectronGood", field="phi", bins=100, start=-3.14, stop=3.14, label=rf"Electron $phi$"),
                Axis(coll="ElectronGood", field="d0_um", bins=100, start=-20, stop=20, label=rf"Electron $d_0$ [$\mu m$]"),
            ],
            only_categories=["pcr"]
        )
    }
)
