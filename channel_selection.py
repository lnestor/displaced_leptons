import awkward as ak
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_definition import Cut
from event_selection import (get_n_back_to_back_muons, get_min_muon_delta_t, get_dilepton_deltaR,
                             get_nElectrons, get_nMuons,
                             get_no_in_material_vtx, MUON_FLAVOR, ELECTRON_FLAVOR)


def ee_cuts(parameters):
    return [
        get_dilepton_deltaR("ee", 0.2, "ElectronGood_ee", "ElectronGood_ee"),
        get_nElectrons(2, "ElectronGood_ee"),
        get_no_in_material_vtx(ELECTRON_FLAVOR, ELECTRON_FLAVOR, "ElectronGood_ee", "ElectronGood_ee"),
    ]


def emu_cuts(parameters):
    return [
        NamedCut(cut=get_nElectrons(1, "ElectronGood_emu"), label=r"$>=1$ electrons passing preselection criteria"),
        NamedCut(cut=get_nMuons(1, "MuonGood_emu"), label=r"$>=1$ muons passing preselection criteria"),
        NamedCut(cut=get_n_back_to_back_muons(0, "MuonGood_emu"), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20, "MuonGood_emu"), label="Veto muon pairs with timing consistent with cosmics"),
        NamedCut(cut=get_dilepton_deltaR("emu", 0.2, "ElectronGood_emu", "MuonGood_emu"), label=r">=1 $e\mu$ pair with $\Delta R>0.2$"),
        NamedCut(cut=get_no_in_material_vtx(MUON_FLAVOR, ELECTRON_FLAVOR, "MuonGood_emu", "ElectronGood_emu"), label=r"No good $e\mu$ vertices in tracker material")
    ]


def mumu_cuts(parameters):
    return [
        get_n_back_to_back_muons(0, "MuonGood_mumu"),
        get_min_muon_delta_t(-20, "MuonGood_mumu"),
        get_dilepton_deltaR("mumu", 0.2, "MuonGood_mumu", "MuonGood_mumu"),
        get_nMuons(2, "MuonGood_mumu"),
        get_no_in_material_vtx(MUON_FLAVOR, MUON_FLAVOR, "MuonGood_mumu", "MuonGood_mumu"),
    ]


# TODO: analysis note lists this veto under "event preselection" but also specifies d0 100-10000
# for the emu inclusive SR — unclear if the veto should include the d0 requirement
def emu_veto(parameters):
    cuts = emu_cuts(parameters)
    def _impl(events, params, year, sample, **kwargs):
        mask = ak.ones_like(events.event, dtype=bool)
        for cut in cuts:
            mask = mask & cut.get_mask(
                events,
                processor_params=kwargs.get("processor_params"),
                year=year,
                sample=sample,
                isMC=kwargs.get("isMC")
            )
        return ~mask
    return Cut(name="emu_veto", params={}, function=_impl)
