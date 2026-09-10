import awkward as ak

from common import (
    get_params,
    get_datasets,
    register_modules,
)
register_modules()

from pocket_coffea.lib.cut_definition import Cut
from lib.named_cut import NamedCut
from lib.configurator import Configurator
from workflow import DisplacedLeptonProcessor

params = get_params()


def _reject_all_impl(events, params, **kwargs):
    return ak.zeros_like(events.event, dtype=bool)


reject_all = Cut(name="reject_all", params={}, function=_reject_all_impl)

cfg = Configurator(
    parameters=params,
    datasets={"jsons": get_datasets("central")},
    workflow=DisplacedLeptonProcessor,
    skim=[NamedCut(cut=reject_all, label="Reject all (genweights-only job)")],
    object_selections={},
    event_preselections=[],
    categories={},
    hists={},
)
