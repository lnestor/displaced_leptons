import awkward as ak
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_definition import Cut
from omegaconf import OmegaConf
from event_selection import (get_n_back_to_back_muons, get_min_muon_delta_t, get_dilepton_deltaR,
                             get_nElectrons, get_nMuons,
                             get_no_in_material_vtx, MUON_FLAVOR, ELECTRON_FLAVOR)


def ee_cuts(parameters):
    return [
        get_dilepton_deltaR("ee", 0.2),
        get_nElectrons(2, OmegaConf.to_container(parameters.categories.ee.Electron)),
        get_no_in_material_vtx(ELECTRON_FLAVOR, ELECTRON_FLAVOR),
    ]


def emu_cuts(parameters):
    return [
        NamedCut(cut=get_nElectrons(1, OmegaConf.to_container(parameters.categories.emu.Electron)), label=r"$>=1$ electrons passing preselection criteria"),
        NamedCut(cut=get_nMuons(1, OmegaConf.to_container(parameters.categories.emu.Muon)), label=r"$>=1$ muons passing preselection criteria"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon pairs with timing consistent with cosmics"),
        NamedCut(cut=get_dilepton_deltaR("emu", 0.2), label=r">=1 $e\mu$ pair with $\Delta R>0.2$"),
        NamedCut(cut=get_no_in_material_vtx(MUON_FLAVOR, ELECTRON_FLAVOR), label=r"No good $e\mu$ vertices in tracker material")
    ]


def mumu_cuts(parameters):
    return [
        get_n_back_to_back_muons(0),
        get_min_muon_delta_t(-20),
        get_dilepton_deltaR("mumu", 0.2),
        get_nMuons(2, OmegaConf.to_container(parameters.categories.mumu.Muon)),
        get_no_in_material_vtx(MUON_FLAVOR, MUON_FLAVOR),
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
