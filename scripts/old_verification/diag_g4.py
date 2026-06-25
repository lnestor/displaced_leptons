"""
Diagnose G4 events: PC last=Stage04_EleEtaPhi, CMSSW last=Stage05_ElePt.

For each event, print all NanoAOD electrons with their cumulative cut masks,
and the CMSSW electron0 pt from Stage04 and Stage05 trees.
"""

import sys
import numpy as np
import uproot
import awkward as ak

G4_EVENTS = [
    (319656, 148, 137270429),
    (319656, 149, 138063127),
    (319678,  75,  73542951),
    (319678, 230, 330732704),
]

NANO_FILE = "nano.root"
CMSSW_FILE = sys.argv[1] if len(sys.argv) > 1 else "hist_Stage00Trigger_2026_06_06_15h14m36s.root"

# 2018 params
ETA_CUT   = 1.5
PT_CUT    = 45.0
SC_LO     = 1.4442
SC_HI     = 1.5660
VETO = dict(eta_min=0.3, eta_max=1.2, phi_min=0.4, phi_max=0.8)


def get_events(f, tree_key, run, lumi, event):
    """Return row index in tree matching (run, lumi, event), or None."""
    arr = f[tree_key].arrays(
        ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
         "electron_ptElectron0", "electron_etaElectron0"],
        library="np",
    )
    mask = (
        (arr["eventvariable_run"].astype(np.uint32) == run) &
        (arr["eventvariable_ls"].astype(np.uint32) == lumi) &
        (arr["eventvariable_event"].astype(np.uint64) == event)
    )
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return None
    i = idx[0]
    return {
        "pt":  arr["electron_ptElectron0"][i],
        "eta": arr["electron_etaElectron0"][i],
    }


def main():
    print(f"Opening {NANO_FILE}...")
    nano = uproot.open(NANO_FILE)
    tree = nano["Events"]

    fields = ["run", "luminosityBlock", "event",
              "Electron_pt", "Electron_eta", "Electron_phi",
              "Electron_deltaEtaSC"]
    arr = tree.arrays(fields, library="ak")

    print(f"Opening {CMSSW_FILE}...")
    cmssw = uproot.open(CMSSW_FILE)

    for (run, lumi, event) in G4_EVENTS:
        print(f"\n{'='*70}")
        print(f"Event: run={run}  lumi={lumi}  event={event}")

        mask = (
            (arr["run"] == run) &
            (arr["luminosityBlock"] == lumi) &
            (arr["event"] == event)
        )
        ev = arr[mask]
        if len(ev) == 0:
            print("  NOT FOUND in NanoAOD")
            continue

        pt    = ak.to_numpy(ev["Electron_pt"][0])
        eta   = ak.to_numpy(ev["Electron_eta"][0])
        phi   = ak.to_numpy(ev["Electron_phi"][0])
        dEta  = ak.to_numpy(ev["Electron_deltaEtaSC"][0])
        etaSC = np.abs(eta + dEta)

        passes_eta    = np.abs(eta) < ETA_CUT
        passes_sc     = ~((etaSC >= SC_LO) & (etaSC <= SC_HI))
        # PC uses strict inequalities
        in_veto_pc    = (
            (eta > VETO["eta_min"]) & (eta < VETO["eta_max"]) &
            (phi > VETO["phi_min"]) & (phi < VETO["phi_max"])
        )
        # CMSSW uses inclusive inequalities
        in_veto_cmssw = (
            (eta >= VETO["eta_min"]) & (eta <= VETO["eta_max"]) &
            (phi >= VETO["phi_min"]) & (phi <= VETO["phi_max"])
        )
        passes_etaphi_pc    = ~in_veto_pc
        passes_etaphi_cmssw = ~in_veto_cmssw
        passes_pt     = pt > PT_CUT

        m_eta         = passes_eta
        m_sc_pc       = m_eta & passes_sc
        m_etaphi_pc   = m_sc_pc & passes_etaphi_pc
        m_etaphi_cmssw= m_sc_pc & passes_etaphi_cmssw
        m_pt_pc       = m_etaphi_pc & passes_pt
        m_pt_cmssw    = m_etaphi_cmssw & passes_pt

        print(f"\n  NanoAOD electrons ({len(pt)} total):")
        print(f"  {'i':>3}  {'pt':>8}  {'eta':>8}  {'phi':>8}  {'etaSC':>8}  "
              f"{'eta<1.5':>7}  {'!SC':>5}  {'!vPC':>5}  {'!vCMS':>6}  {'pt>45':>6}")
        for i in range(len(pt)):
            print(f"  {i:>3}  {pt[i]:>8.3f}  {eta[i]:>8.4f}  {phi[i]:>8.4f}  {etaSC[i]:>8.4f}  "
                  f"  {passes_eta[i]!s:>5}  {passes_sc[i]!s:>5}  "
                  f"{passes_etaphi_pc[i]!s:>5}  {passes_etaphi_cmssw[i]!s:>5}  "
                  f"  {passes_pt[i]!s:>5}")

        n_pc    = np.sum(m_etaphi_pc)
        n_cmssw = np.sum(m_etaphi_cmssw)
        n_pt_pc    = np.sum(m_pt_pc)
        n_pt_cmssw = np.sum(m_pt_cmssw)

        print(f"\n  After etaphi veto: PC={n_pc}  CMSSW={n_cmssw}")
        print(f"  After pt cut:      PC={n_pt_pc}  CMSSW={n_pt_cmssw}")
        if n_pt_pc == 0 and n_pt_cmssw > 0:
            print("  --> G4 pattern confirmed from boundary difference")
        elif n_pt_pc == 0 and n_pt_cmssw == 0:
            print("  --> Both fail pt cut; difference must be pt value MiniAOD vs NanoAOD")

        # CMSSW Stage04 and Stage05 entries
        r4 = get_events(cmssw, "Stage04EleEtaPhiVetoTreeMaker/Tree", run, lumi, event)
        r5 = get_events(cmssw, "Stage05ElePtTreeMaker/Tree",          run, lumi, event)
        print(f"\n  CMSSW Stage04 electron0: pt={r4['pt']:.3f}  eta={r4['eta']:.4f}" if r4 else "  CMSSW Stage04: not found")
        print(f"  CMSSW Stage05 electron0: pt={r5['pt']:.3f}  eta={r5['eta']:.4f}" if r5 else "  CMSSW Stage05: not found")


if __name__ == "__main__":
    main()
