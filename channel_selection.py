import awkward as ak
from pocket_coffea.lib.cut_definition import Cut
from omegaconf import OmegaConf
from event_selection import b2b_muons_mask, delta_r_mask, nObj_mask


def _ee_impl(events, params, year, sample, **kwargs):
    mask = delta_r_mask(events.ElectronGood, events.ElectronGood, 0.2)
    mask = mask & nObj_mask(events.ElectronGood, 2, params["electron_pts"][year])
    return mask

def ee_channel(parameters):
    return Cut(
        name="ee",
        params={"electron_pts": OmegaConf.to_container(parameters.categories.ee.Electron)},
        function=_ee_impl,
    )


def _emu_impl(events, params, year, sample, **kwargs):
    mask = b2b_muons_mask(events)
    mask = mask & delta_r_mask(events.ElectronGood, events.MuonGood, 0.2)
    mask = mask & nObj_mask(events.ElectronGood, 1, params["electron_pts"][year])
    mask = mask & nObj_mask(events.MuonGood, 1, params["muon_pts"][year])
    return mask

def emu_channel(parameters):
    return Cut(
        name="emu",
        params={
            "electron_pts": OmegaConf.to_container(parameters.categories.emu.Electron),
            "muon_pts": OmegaConf.to_container(parameters.categories.emu.Muon),
        },
        function=_emu_impl,
    )


def _mumu_impl(events, params, year, sample, **kwargs):
    mask = b2b_muons_mask(events)
    mask = mask & delta_r_mask(events.MuonGood, events.MuonGood, 0.2)
    mask = mask & nObj_mask(events.MuonGood, 2, params["muon_pts"][year])
    return mask

def mumu_channel(parameters):
    return Cut(
        name="mumu",
        params={"muon_pts": OmegaConf.to_container(parameters.categories.mumu.Muon)},
        function=_mumu_impl,
    )


# TODO: analysis note lists this veto under "event preselection" but also specifies d0 100-10000
# for the emu inclusive SR — unclear if the veto should include the d0 requirement
def _emu_veto_impl(events, params, year, sample, **kwargs):
    return ~_emu_impl(events, params, year, sample, **kwargs)

def emu_veto(parameters):
    return Cut(
        name="emu_veto",
        params={
            "electron_pts": OmegaConf.to_container(parameters.categories.emu.Electron),
            "muon_pts": OmegaConf.to_container(parameters.categories.emu.Muon),
        },
        function=_emu_veto_impl,
    )
