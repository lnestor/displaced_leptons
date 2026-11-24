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
from lib.cuts.generic import get_d0_lt
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

LEPTON_D0_BINS_UM = (
    list(range(-10000, -1000, 250))
    + list(range(-1000, -200, 25))
    + list(range(-200, 200, 5))
    + list(range(200, 1000, 25))
    + list(range(1000, 10001, 250))
)
DATA_SAMPLES = ["MuonEG"]
MC_PROMPT_LEPTON_ABSD0_BINS_UM = [0, 25, 50, 75, 100, 150, 200, 500, 1000]
DATA_PROMPT_LEPTON_ABSD0_BINS_UM = [
    edge for edge in MC_PROMPT_LEPTON_ABSD0_BINS_UM if edge <= SR_THRESHOLD
]
LEPTON_PT_BINS_GEV = [0, 50, 75, 100, 150, 250]


def define_lepton_index(events, year, is_mc, supplement_version):
    for coll in ["ElectronGood", "MuonGood"]:
        events[coll, "index"] = ak.local_index(events[coll], axis=1)


def define_leading_other_flavor_absd0(events, year, is_mc, supplement_version):
    electrons = events.ElectronGood
    muons = events.MuonGood
    leading_electron_absd0 = ak.firsts(electrons.absd0_um)
    leading_muon_absd0 = ak.firsts(muons.absd0_um)
    events["MuonGood", "leading_electron_absd0_um"] = ak.broadcast_arrays(leading_electron_absd0, muons.absd0_um)[0]
    events["ElectronGood", "leading_muon_absd0_um"] = ak.broadcast_arrays(leading_muon_absd0, electrons.absd0_um)[0]


def lepton_d0_hist(filled_flavor, prompt_flavor, category, prompt_absd0_bins, **sample_filter):
    coll = f"{filled_flavor}Good"
    return HistConf([
        Axis(
            coll=coll,
            field="d0_um",
            type="variable",
            bins=LEPTON_D0_BINS_UM,
            label=rf"{filled_flavor} $d_0$ [$\mu m$]"
        ),
        Axis(
            coll=coll,
            field=f"leading_{prompt_flavor.lower()}_absd0_um",
            type="variable",
            bins=prompt_absd0_bins,
            label=rf"Leading {prompt_flavor.lower()} $|d_0|$ [$\mu m$]"
        ),
        Axis(
            coll=coll,
            field="pt",
            type="variable",
            bins=LEPTON_PT_BINS_GEV,
            label=rf"{filled_flavor} $p_T$ [GeV]"
        ),
        Axis(
            coll=coll,
            field="index",
            bins=3,
            start=0,
            stop=3,
            label=f"{filled_flavor} index"
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
    skim = get_default_skim_cuts(sample="MuonEG"),
    custom_fields = {
        "preselection": {
            "common": [define_custom_nano_fields],
            "bysample": {"DY": [define_DY_flavor]}
        },
        "postselection": {
            "common": [define_lepton_index, define_leading_other_flavor_absd0]
        },
    },
    object_selections = {"Electron": get_ele_cuts("emu"), "Muon": get_mu_cuts("emu")},
    event_preselections = [
        NamedCut(get_nObj_min(1, coll="ElectronGood"), ">= 1 good electrons"),
        NamedCut(get_nObj_min(1, coll="MuonGood"), ">= 1 good muons"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon paris with timing consistent with cosmics"),
        NamedCut(cut=get_min_deltaR("ElectronGood", "MuonGood", 0.2), label="Dilepton dleta R"),
        NamedCut(cut=get_no_in_material_vtx(channel="emu"), label="Material vtx")
    ],
    categories = {
        "sideband_electron": [get_d0_lt("ElectronGood", SR_THRESHOLD, pos=0)],
        "sideband_muon": [get_d0_lt("MuonGood", SR_THRESHOLD, pos=0)],
        "no_d0_cut": [passthrough],
    },
    hists = {
        "sideband_electron": lepton_d0_hist(
            "Muon", "Electron", "sideband_electron", DATA_PROMPT_LEPTON_ABSD0_BINS_UM, only_samples=DATA_SAMPLES
        ),
        "sideband_muon": lepton_d0_hist(
            "Electron", "Muon", "sideband_muon", DATA_PROMPT_LEPTON_ABSD0_BINS_UM, only_samples=DATA_SAMPLES
        ),
        "no_d0_cut_electron": lepton_d0_hist(
            "Muon", "Electron", "no_d0_cut", MC_PROMPT_LEPTON_ABSD0_BINS_UM, exclude_samples=DATA_SAMPLES
        ),
        "no_d0_cut_muon": lepton_d0_hist(
            "Electron", "Muon", "no_d0_cut", MC_PROMPT_LEPTON_ABSD0_BINS_UM, exclude_samples=DATA_SAMPLES
        ),
    },
    calibrators = [ElectronsScaleCalibrator, MuonsCalibrator], # No d0 correction calibrator
)
