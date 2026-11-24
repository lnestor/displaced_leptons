import awkward as ak

from lib.configuration import (
    DY_SUBSAMPLES,
    MC_SAMPLES,
    RUN_3_YEARS,
    get_datasets,
    get_default_skim_cuts,
    get_ele_cuts,
    get_mu_cuts,
    get_params,
    get_supplements,
    register_modules
)
from lib.cuts.event_selection import (
    get_n_back_to_back_muons,
    get_min_muon_delta_t,
    get_min_deltaR,
    get_no_in_material_vtx
)
from lib.cuts.generic import get_d0_gt, get_d0_lt, invert_cut
from lib.configurator import Configurator
from lib.custom_fields import define_custom_nano_fields, define_DY_flavor
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_functions import get_nObj_min
from pocket_coffea.parameters.cuts import passthrough
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from pocket_coffea.parameters.histograms import HistConf, Axis
from lib.workflow.analysis_processor import AnalysisProcessor

register_modules()
params = get_params()

SR_THRESHOLD = 100

MUON_D0_BINS_UM = (
    list(range(-10000, -1000, 250))
    + list(range(-1000, -200, 25))
    + list(range(-200, 200, 5))
    + list(range(200, 1000, 25))
    + list(range(1000, 10001, 250))
)
DATA_SAMPLES = ["Muon"]
MC_PROMPT_MUON_ABSD0_BINS_UM = [0, 25, 50, 75, 100, 150, 200, 500, 1000]
DATA_PROMPT_MUON_ABSD0_BINS_UM = [
    edge for edge in MC_PROMPT_MUON_ABSD0_BINS_UM if edge <= SR_THRESHOLD
]
MUON_PT_BINS_GEV = [0, 50, 75, 100, 150, 250]


def define_muon_index(events, year, is_mc, supplement_version):
    muons = events.MuonGood
    events["MuonGood", "index"] = ak.local_index(muons, axis=1)


def define_leading_and_subleading_absd0(events, year, is_mc, supplement_version):
    muons = events.MuonGood
    leading_absd0 = ak.firsts(muons.absd0_um)
    subleading_absd0 = ak.firsts(muons[:, 1:].absd0_um)
    events["MuonGood", "leading_absd0_um"] = ak.broadcast_arrays(leading_absd0, muons.absd0_um)[0]
    events["MuonGood", "subleading_absd0_um"] = ak.broadcast_arrays(subleading_absd0, muons.absd0_um)[0]


def muon_d0_hist(prompt_muon, category, prompt_absd0_bins, **sample_filter):
    return HistConf([
        Axis(
            coll="MuonGood",
            field="d0_um",
            type="variable",
            bins=MUON_D0_BINS_UM,
            label=r"Muon $d_0$ [$\mu m$]"
        ),
        Axis(
            coll="MuonGood",
            field=f"{prompt_muon}_absd0_um",
            type="variable",
            bins=prompt_absd0_bins,
            label=rf"{prompt_muon.capitalize()} muon $|d_0|$ [$\mu m$]"
        ),
        Axis(
            coll="MuonGood",
            field="pt",
            type="variable",
            bins=MUON_PT_BINS_GEV,
            label=r"Muon $p_T$ [GeV]"
        ),
        Axis(
            coll="MuonGood",
            field="index",
            bins=3,
            start=0,
            stop=3,
            label="Muon index"
        ),
    ], only_categories=[category], **sample_filter)


cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": [*DATA_SAMPLES, *MC_SAMPLES],
            "year": RUN_3_YEARS
        },
        "subsamples": DY_SUBSAMPLES,
        "priority": [*DATA_SAMPLES, "DY", "TTbar", "Diboson"]
    },
    supplements = {"jsons": get_supplements("supplements")},
    workflow = AnalysisProcessor,
    skim = get_default_skim_cuts(sample="Muon"),
    custom_fields = {
        "preselection": {
            "common": [define_custom_nano_fields],
            "bysample": {"DY": [define_DY_flavor]}
        },
        "postselection": {
            "common": [define_muon_index, define_leading_and_subleading_absd0]
        },
    },
    object_selections = {
        "Electron": get_ele_cuts("emu"),
        "Muon": get_mu_cuts("mumu")
    },
    event_preselections = [
        NamedCut(get_nObj_min(2, coll="MuonGood"), ">= 2 good muons"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("MuonGood", "MuonGood", 0.2), label="Dilepton delta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="mumu"), label="Material vtx"),
        NamedCut(cut=invert_cut(get_d0_gt("ElectronGood", 100)), label="emu veto")
    ],
    categories = {
        "sideband_leading": [get_d0_lt("MuonGood", SR_THRESHOLD, pos=0)],
        "sideband_subleading": [get_d0_lt("MuonGood", SR_THRESHOLD, pos=1)],
        "no_d0_cut": [passthrough],
    },
    hists = {
        "sideband_leading": muon_d0_hist(
            "leading", "sideband_leading", DATA_PROMPT_MUON_ABSD0_BINS_UM, only_samples=DATA_SAMPLES
        ),
        "sideband_subleading": muon_d0_hist(
            "subleading", "sideband_subleading", DATA_PROMPT_MUON_ABSD0_BINS_UM, only_samples=DATA_SAMPLES
        ),
        "no_d0_cut_leading": muon_d0_hist(
            "leading", "no_d0_cut", MC_PROMPT_MUON_ABSD0_BINS_UM, exclude_samples=DATA_SAMPLES
        ),
        "no_d0_cut_subleading": muon_d0_hist(
            "subleading", "no_d0_cut", MC_PROMPT_MUON_ABSD0_BINS_UM, exclude_samples=DATA_SAMPLES
        ),
    },
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator], # No d0 correction calibrator
)
