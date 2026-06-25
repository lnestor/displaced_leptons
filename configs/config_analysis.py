from common import (
    DATA_SAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    DEFAULT_WEIGHTS,
    DEFAULT_VARIATIONS,
    DEFAULT_CALIBRATORS,
    DEFAULT_SKIM_CUTS,
    get_channel_categories,
    get_params,
    get_datasets,
    register_modules,
)
register_modules()

from workflow import DisplacedLeptonProcessor
from pocket_coffea.utils.configurator import Configurator
from hists import lepton_hists, background_hists

params = get_params()

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": [*DATA_SAMPLES, *MC_SAMPLES],
            "samples_exclude": [],
            "year": RUN_3_YEARS
        }
    },
    workflow = DisplacedLeptonProcessor,
    skim = DEFAULT_SKIM_CUTS,
    categories = get_channel_categories(params, include_pcr=True),
    variables = {
        **lepton_hists(coll="ElectronGood", label="Electron"),
        **lepton_hists(coll="MuonGood", label="Muon"),
        **background_hists()
    },
    preselections = [],
    calibrators = DEFAULT_CALIBRATORS,
    weights = DEFAULT_WEIGHTS,
    variations = DEFAULT_VARIATIONS,
)
