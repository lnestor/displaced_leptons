from common import (
    DEFAULT_WEIGHTS,
    DEFAULT_VARIATIONS,
    DEFAULT_CALIBRATORS,
    DEFAULT_SKIM_CUTS,
    get_channel_categories,
    get_params,
    register_modules,
    get_datasets
)

register_modules()

from workflow import DisplacedLeptonProcessor
from pocket_coffea.utils.configurator import Configurator
from pocket_coffea.parameters.histograms import HistConf, Axis
from pocket_coffea.lib.cut_functions import get_HLTsel_custom
from hists import lepton_hists

params = get_params()
base_cats = get_channel_categories(params, add_veto=False)

EE_TRIGGERS = [
    "HLT_DoublePhoton70",
    "HLT_DoublePhoton85",
    "HLT_DiEle27_WPTightCaloOnly_L1DoubleEG",
    "HLT_Diphoton30_22_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90",
    "HLT_Diphoton30_22_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass95",
    "HLT_Diphoton30_18_R9IdL_AND_HE_AND_IsoCaloId",
    "HLT_Diphoton30_18_R9IdL_AND_HE_AND_IsoCaloId_Mass55",
    "HLT_Diphoton24_14_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_Diphoton24_16_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_Diphoton22_14_eta1p5_R9IdL_AND_HET_AND_IsoTCaloIdT",
    "HLT_DiphotonMVA14p25_Mass90",
    "HLT_DiphotonMVA14p25_Tight_Mass90"
]

MUMU_TRIGGERS = [
    # Direct Run 2 equivalents
    "HLT_DoubleMu43NoFiltersNoVtx",
    "HLT_DoubleMu48NoFiltersNoVtx",
    # DoubleL3 NoVtx with explicit Dxy minimum
    "HLT_DoubleL3Mu16_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3Mu18_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3Mu20_10NoVtx_DxyMin0p01cm",
    "HLT_DoubleL3dTksMu16_10NoVtx_DxyMin0p01cm",
    # DoubleL2 NoVtx (L2-only, standard seed)
    "HLT_DoubleL2Mu23NoVtx_2Cha",
    "HLT_DoubleL2Mu25NoVtx_2Cha",
    "HLT_DoubleL2Mu25NoVtx_2Cha_Eta2p4",
    "HLT_DoubleL2Mu30NoVtx_2Cha_Eta2p4",
    # DoubleL2 NoVtx (cosmic seed)
    "HLT_DoubleL2Mu23NoVtx_2Cha_CosmicSeed",
    "HLT_DoubleL2Mu25NoVtx_2Cha_CosmicSeed",
    "HLT_DoubleL2Mu25NoVtx_2Cha_CosmicSeed_Eta2p4",
    "HLT_DoubleL2Mu30NoVtx_2Cha_CosmicSeed_Eta2p4",
    # DoubleL2 NoVtx with veto on prompt L3 muons
    "HLT_DoubleL2Mu10NoVtx_2Cha_VetoL3Mu0DxyMax1cm",
    "HLT_DoubleL2Mu12NoVtx_2Cha_VetoL3Mu0DxyMax1cm",
    "HLT_DoubleL2Mu14NoVtx_2Cha_VetoL3Mu0DxyMax1cm",
    "HLT_DoubleL2Mu10NoVtx_2Cha_CosmicSeed_VetoL3Mu0DxyMax1cm",
    "HLT_DoubleL2Mu12NoVtx_2Cha_CosmicSeed_VetoL3Mu0DxyMax1cm",
    # DoubleL2 + single L3 hybrid
    "HLT_DoubleL2Mu_L3Mu16NoVtx_VetoL3Mu0DxyMax0p1cm",
    "HLT_DoubleL2Mu_L3Mu18NoVtx_VetoL3Mu0DxyMax0p1cm",
]

EMU_TRIGGERS = [
    "HLT_Mu38NoFiltersNoVtxDisplaced_Photon38_CaloIdL",
    "HLT_Mu43NoFiltersNoVtxDisplaced_Photon43_CaloIdL",
    "HLT_Mu43NoFiltersNoVtx_Photon43_CaloIdL",
    "HLT_Mu48NoFiltersNoVtx_Photon48_CaloIdL",
    "HLT_Mu20NoFiltersNoVtxDisplaced_Photon20_CaloCustomId"
]

def add_trigger_cats(channel_name, base_cuts, triggers):
    cats = {}
    for trigger in triggers:
        cats[f"{channel_name}_{trigger}"] = [*base_cuts, get_HLTsel_custom([trigger])]
    return cats

cfg = Configurator(
    parameters = params,
    datasets = {
        "jsons": get_datasets("central"),
        "filter": {
            "samples": ["MET"],
            "samples_exclude": [],
            "year": ["2024"]
        }
    },
    workflow = DisplacedLeptonProcessor,
    workflow_options = { "skip_pt_cut": True },
    skim = DEFAULT_SKIM_CUTS,
    categories = {
        **base_cats,
        **add_trigger_cats("ee", base_cats["ee"], EE_TRIGGERS),
        **add_trigger_cats("emu", base_cats["emu"], EMU_TRIGGERS),
        **add_trigger_cats("mumu", base_cats["mumu"], MUMU_TRIGGERS)
    },
    variables = {
        "AllElectron_pt": HistConf([Axis(coll="ElectronGood", field="pt", bins=50, start=0, stop=500, label=rf"Leading electron $p_T$ [GeV]")]),
        "LeadingElectron_pt": HistConf([Axis(coll="ElectronGood", pos=0, field="pt", bins=50, start=0, stop=500, label=rf"Leading electron $p_T$ [GeV]")]),
        "SubleadingElectron_pt": HistConf([Axis(coll="ElectronGood", pos=1, field="pt", bins=50, start=0, stop=500, label=rf"Subleading electron $p_T$ [GeV]")]),
        "AllMuon_pt": HistConf([Axis(coll="MuonGood", field="pt", bins=50, start=0, stop=500, label=rf"Leading muon $p_T$ [GeV]")]),
        "LeadingMuon_pt": HistConf([Axis(coll="MuonGood", pos=0, field="pt", bins=50, start=0, stop=500, label=rf"Leading muon $p_T$ [GeV]")]),
        "SubleadingMuon_pt": HistConf([Axis(coll="MuonGood", pos=1, field="pt", bins=50, start=0, stop=500, label=rf"Subleading muon $p_T$ [GeV]")])
    },
    preselections = [],
    calibrators = DEFAULT_CALIBRATORS,
    weights = DEFAULT_WEIGHTS,
    variations = DEFAULT_VARIATIONS,
)
