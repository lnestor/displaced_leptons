import awkward as ak
import numpy as np

def displaced_lepton_selection(events, lepton_flavor, year, params):
    leptons = events[lepton_flavor]
    cuts = params.object_preselection[lepton_flavor][year]

    passes_pt = leptons.pt > cuts.pt
    passes_eta = abs(leptons.eta) < cuts.eta

    if "etaphi_veto" in cuts.keys():
        mask = (
            (leptons.eta > cuts.etaphi_veto.eta_min) &
            (leptons.eta < cuts.etaphi_veto.eta_max) &
            (leptons.phi > cuts.etaphi_veto.phi_min) &
            (leptons.phi < cuts.etaphi_veto.phi_max)
        )

        passes_etaphi_veto = ~mask
    else:
        passes_etaphi_veto = ak.ones_like(leptons.pt, dtype=bool)


    if lepton_flavor == "Electron":
        passes_id = leptons[cuts.id] == cuts.id_req
        etaSC = abs(leptons.deltaEtaSC + leptons.eta)
        passes_SC = np.invert((etaSC >= 1.442) & (etaSC <= 1.5660))

        if year == "2016":
            passes_iso = leptons.pfRelIso03_all < cuts["iso"]
        else:
            passes_iso = leptons.pfRelIso03_all < cuts["iso_base"] + cuts["iso_pt_dep"] / leptons.pt

    elif lepton_flavor == "Muon":
        passes_id = leptons[cuts.id] == True
        passes_SC = ak.ones_like(leptons.pt, dtype=bool)
        passes_iso = leptons.pfRelIso04_all < cuts["iso"]
    else:
        raise ValueError(f"Lepton type {lepton_flavor} not supported for object preselection.")


    good_leptons = (
        passes_pt &
        passes_eta &
        passes_etaphi_veto &
        passes_id &
        passes_SC &
        passes_iso
    )

    leptons = ak.with_field(leptons, ak.local_index(leptons, axis=1), "original_idx")
    return leptons[good_leptons]
