"""
Targeted diagnostic for the 2 events causing the Stage07 EleIso count difference.

Event A (run=319656, lumi=141, event=123130527):
  PC last=Stage02_EleEta (fails Stage03_EleSC)
  CMSSW last=Stage09_MuEtaPhi (passes SC gap veto)
  -> Disagreement on SC gap cut

Event B (run=319656, lumi=124, event=96217529):
  PC last=Stage05_ElePt (fails Stage06_EleID)
  CMSSW last=Stage17_NoDispVtx (passes all cuts)
  -> Disagreement on electron ID

Usage:
    python diag_2events.py <cmssw_hist_file> <nano_file>
"""

import sys
import numpy as np
import uproot
import awkward as ak

EVENT_A = (319656, 141, 123130527)  # SC gap disagreement
EVENT_B = (319656, 124,  96217529)  # EleID disagreement

CMSSW_TREES = {
    "Stage02_EleEta":    "Stage02EleEtaTreeMaker/Tree",
    "Stage03_EleSC":     "Stage03EleGapVetoTreeMaker/Tree",
    "Stage09_MuEtaPhi":  "Stage09MuEtaPhiVetoTreeMaker/Tree",
    "Stage05_ElePt":     "Stage05ElePtTreeMaker/Tree",
    "Stage06_EleID":     "Stage06EleIDTreeMaker/Tree",
    "Stage17_NoDispVtx": "Stage17NoDispVtxTreeMaker/Tree",
}

CMSSW_ELE_BRANCHES = [
    "eventvariable_run", "eventvariable_ls", "eventvariable_event",
    "electron_ptElectron0", "electron_etaElectron0",
    "electron_absDeltaEtaSuperClusterTrackAtVtxElectron0",
]


def load_cmssw_events(hist_file, targets):
    """Return dict[stage][event_id] -> branch dict."""
    f = uproot.open(hist_file)
    result = {stage: {} for stage in CMSSW_TREES}
    for stage, tree_key in CMSSW_TREES.items():
        if tree_key not in f:
            continue
        arr = f[tree_key].arrays(CMSSW_ELE_BRANCHES, library="np")
        for i in range(len(arr["eventvariable_run"])):
            ev = (int(arr["eventvariable_run"][i]),
                  int(arr["eventvariable_ls"][i]),
                  int(arr["eventvariable_event"][i]))
            if ev in targets:
                result[stage][ev] = {b: float(arr[b][i]) for b in CMSSW_ELE_BRANCHES
                                     if b not in ("eventvariable_run","eventvariable_ls","eventvariable_event")}
    return result


def load_nano_electrons(nano_file, targets):
    """Return dict[event_id] -> list of per-electron dicts."""
    nano = uproot.open(nano_file)["Events"]
    arrays = nano.arrays(
        ["run", "luminosityBlock", "event",
         "Electron_pt", "Electron_eta", "Electron_deltaEtaSC", "Electron_cutBased"],
        library="ak"
    )
    result = {}
    for i in range(len(arrays)):
        ev = (int(arrays["run"][i]),
              int(arrays["luminosityBlock"][i]),
              int(arrays["event"][i]))
        if ev not in targets:
            continue
        eles = []
        for j in range(len(arrays["Electron_pt"][i])):
            eta    = float(arrays["Electron_eta"][i][j])
            dEtaSC = float(arrays["Electron_deltaEtaSC"][i][j])
            etaSC  = abs(eta + dEtaSC)
            in_gap = (etaSC >= 1.4442) and (etaSC <= 1.5660)
            eles.append({
                "pt":       float(arrays["Electron_pt"][i][j]),
                "eta":      eta,
                "deltaEtaSC": dEtaSC,
                "etaSC":    etaSC,
                "in_gap":   in_gap,
                "cutBased": int(arrays["Electron_cutBased"][i][j]),
            })
        result[ev] = eles
    return result


def print_event(label, ev, cmssw, nano_eles):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  run={ev[0]}  lumi={ev[1]}  event={ev[2]}")
    print(f"{'='*70}")

    print(f"\n  NanoAOD electrons ({len(nano_eles)} total):")
    if not nano_eles:
        print("    (none)")
    else:
        print(f"    {'pt':>7}  {'eta':>8}  {'etaSC':>8}  {'in_gap':>7}  {'cutBased':>9}")
        for e in nano_eles:
            print(f"    {e['pt']:>7.3f}  {e['eta']:>8.4f}  {e['etaSC']:>8.4f}  {str(e['in_gap']):>7}  {e['cutBased']:>9}")

    print(f"\n  CMSSW leading electron per stage:")
    print(f"    {'stage':<22}  {'in tree':>7}  {'pt':>7}  {'eta':>8}  {'|dEtaSC|':>9}")
    for stage in CMSSW_TREES:
        if ev in cmssw[stage]:
            d = cmssw[stage][ev]
            print(f"    {stage:<22}  {'yes':>7}  {d['electron_ptElectron0']:>7.3f}  "
                  f"{d['electron_etaElectron0']:>8.4f}  "
                  f"{d['electron_absDeltaEtaSuperClusterTrackAtVtxElectron0']:>9.5f}")
        else:
            print(f"    {stage:<22}  {'no':>7}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python diag_2events.py <cmssw_hist_file> <nano_file>")
        sys.exit(1)

    hist_file, nano_file = sys.argv[1], sys.argv[2]
    targets = {EVENT_A, EVENT_B}

    print("Loading CMSSW trees...")
    cmssw = load_cmssw_events(hist_file, targets)
    print("Loading NanoAOD...")
    nano = load_nano_electrons(nano_file, targets)

    print_event(
        "Event A: SC gap disagreement (PC fails Stage03_EleSC, CMSSW passes Stage09)",
        EVENT_A, cmssw, nano.get(EVENT_A, [])
    )
    print_event(
        "Event B: EleID disagreement (PC fails Stage06_EleID, CMSSW passes Stage17)",
        EVENT_B, cmssw, nano.get(EVENT_B, [])
    )

    print(f"\n  Notes:")
    print(f"    PC SC gap cut:  etaSC = |eta + deltaEtaSC| in [1.4442, 1.5660] -> remove")
    print(f"    CMSSW SC gap:   isEBEEGap = 0 (stored as boolean in CMSSW)")
    print(f"    PC EleID cut:   cutBased >= 4 (tight)")
    print(f"    CMSSW EleID:    passesVID_tightID")


if __name__ == "__main__":
    main()
