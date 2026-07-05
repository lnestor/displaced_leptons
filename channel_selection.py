import awkward as ak
from lib.named_cut import NamedCut
from pocket_coffea.lib.cut_definition import Cut


def emu_cuts(parameters, skip_pt=False):
    e_min_pts = OmegaConf.to_container(parameters.categories.emu.Electron)
    mu_min_pts = OmegaConf.to_container(parameters.categories.emu.Muon)
    if skip_pt:
        e_min_pts = _zero_pts(e_min_pts)
        mu_min_pts = _zero_pts(mu_min_pts)
    return [
        NamedCut(cut=get_nElectrons(1, e_min_pts), label=r"$>=1$ electrons passing preselection criteria"),
        NamedCut(cut=get_nMuons(1, mu_min_pts), label=r"$>=1$ muons passing preselection criteria"),
        NamedCut(cut=get_n_back_to_back_muons(0), label="Veto back to back muons"),
        NamedCut(cut=get_min_muon_delta_t(-20), label="Veto muon pairs with timing consistent with cosmics"),
        NamedCut(cut=get_dilepton_deltaR("emu", 0.2), label=r">=1 $e\mu$ pair with $\Delta R>0.2$"),
        NamedCut(cut=get_no_in_material_vtx(MUON_FLAVOR, ELECTRON_FLAVOR), label=r"No good $e\mu$ vertices in tracker material")
    ]


# TODO: analysis note lists this veto under "event preselection" but also specifies d0 100-10000
# for the emu inclusive SR — unclear if the veto should include the d0 requirement
def emu_veto(parameters, skip_pt=False):
    cuts = emu_cuts(parameters, skip_pt=skip_pt)
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
