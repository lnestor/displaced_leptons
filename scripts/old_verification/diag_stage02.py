"""
Diagnostic for Stage02 EleEta disagreements.

For events where PC last=Stage00_Trigger and CMSSW last=Stage04_EleEtaPhi:
  - Print all Electron.eta values from the NanoAOD
  - Print electron_etaElectron0 from CMSSW Stage04 tree

Usage:
    python diag_stage02.py <coffea_file> <cmssw_hist_file> <nano_file>
"""

import sys
import numpy as np
import uproot
import awkward as ak
from coffea.util import load

PC_STAGES = [
    "Stage00_Trigger",
    "Stage02_EleEta",
    "Stage03_EleSC",
    "Stage04_EleEtaPhi",
    "Stage05_ElePt",
    "Stage06_EleID",
    "Stage07_EleIso",
    "Stage08_MuEta",
    "Stage09_MuEtaPhi",
    "Stage10_MuPt",
    "Stage11_MuGlobal",
    "Stage12_MuID",
    "Stage13_MuIso",
    "Stage14_CosAlpha",
    "Stage15_DeltaT",
    "Stage16_DeltaR",
    "Stage17_NoDispVtx",
]

CMSSW_TREE = {
    "Stage00_Trigger":   "Stage01JetBasicTreeMaker/Tree",
    "Stage02_EleEta":    "Stage02EleEtaTreeMaker/Tree",
    "Stage03_EleSC":     "Stage03EleGapVetoTreeMaker/Tree",
    "Stage04_EleEtaPhi": "Stage04EleEtaPhiVetoTreeMaker/Tree",
    "Stage05_ElePt":     "Stage05ElePtTreeMaker/Tree",
    "Stage06_EleID":     "Stage06EleIDTreeMaker/Tree",
    "Stage07_EleIso":    "Stage07EleIsoTreeMaker/Tree",
    "Stage08_MuEta":     "Stage08MuEtaTreeMaker/Tree",
    "Stage09_MuEtaPhi":  "Stage09MuEtaPhiVetoTreeMaker/Tree",
    "Stage10_MuPt":      "Stage10MuPtTreeMaker/Tree",
    "Stage11_MuGlobal":  "Stage11MuGlobalTreeMaker/Tree",
    "Stage12_MuID":      "Stage12MuIDTreeMaker/Tree",
    "Stage13_MuIso":     "Stage13MuIsoTreeMaker/Tree",
    "Stage14_CosAlpha":  "Stage14CosAlphaVetoTreeMaker/Tree",
    "Stage15_DeltaT":    "Stage15DeltaTVetoTreeMaker/Tree",
    "Stage16_DeltaR":    "Stage16EMuDeltaRTreeMaker/Tree",
    "Stage17_NoDispVtx": "Stage17NoDispVtxTreeMaker/Tree",
}

MAX_PRINT = 20


def last_stage_passed(event_id, sets):
    last = None
    for label in PC_STAGES:
        if label in sets and event_id in sets[label]:
            last = label
    return last


def main():
    if len(sys.argv) != 4:
        print("Usage: python diag_stage02.py <coffea_file> <cmssw_hist_file> <nano_file>")
        sys.exit(1)

    coffea_file, hist_file, nano_file = sys.argv[1], sys.argv[2], sys.argv[3]

    # --- Load PC output ---
    print("Loading PocketCoffea output...")
    output = load(coffea_file)
    pc_sets = {}
    for label, fields in output["stage_events"].items():
        if not fields:
            continue
        d = {f: fields[f].value for f in fields}
        pc_sets[label] = set(zip(d["run"].tolist(), d["lumi"].tolist(), d["event"].tolist()))

    # --- Load CMSSW output ---
    print("Loading CMSSW output...")
    cmssw_sets = {}
    cmssw_eta = {}  # stage -> {(run,lumi,event): electron_etaElectron0}
    f = uproot.open(hist_file)
    for label, tree_key in CMSSW_TREE.items():
        if tree_key not in f:
            continue
        arr = f[tree_key].arrays(
            ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
             "electron_etaElectron0", "electron_ptElectron0"],
            library="np",
        )
        ids = list(zip(
            arr["eventvariable_run"].astype(int).tolist(),
            arr["eventvariable_ls"].astype(int).tolist(),
            arr["eventvariable_event"].astype(int).tolist(),
        ))
        cmssw_sets[label] = set(ids)
        cmssw_eta[label] = {ev: (float(arr["electron_ptElectron0"][i]),
                                 float(arr["electron_etaElectron0"][i]))
                            for i, ev in enumerate(ids)}

    # --- Find disagreeing events ---
    all_events = pc_sets.get("Stage00_Trigger", set())

    groups = {
        ("Stage00_Trigger", "Stage02_EleEta"):   [],
        ("Stage00_Trigger", "Stage03_EleSC"):    [],
        ("Stage00_Trigger", "Stage04_EleEtaPhi"):[],
    }
    for ev in sorted(all_events):
        pc_last    = last_stage_passed(ev, pc_sets)
        cmssw_last = last_stage_passed(ev, cmssw_sets)
        key = (pc_last, cmssw_last)
        if key in groups:
            groups[key].append(ev)

    # --- pt check for each group ---
    def check_pt(evts, cmssw_stage):
        n_lt5, n_ge5, n_missing = 0, 0, 0
        for ev in evts:
            entry = cmssw_eta.get(cmssw_stage, {}).get(ev)
            if entry is None:
                n_missing += 1
                continue
            pt, _ = entry
            if pt < 5.0:
                n_lt5 += 1
            else:
                n_ge5 += 1
        return n_lt5, n_ge5, n_missing

    print(f"\n{'Group':<50} {'total':>6} {'pt<5':>6} {'pt>=5':>6} {'missing':>7}")
    print("-" * 80)
    for (pc_last, cmssw_last), evts in groups.items():
        n_lt5, n_ge5, n_missing = check_pt(evts, cmssw_last)
        label = f"PC={pc_last}  CMSSW={cmssw_last}"
        print(f"  {label:<48} {len(evts):>6} {n_lt5:>6} {n_ge5:>6} {n_missing:>7}")

    print(f"\nOf {len(groups[('Stage00_Trigger','Stage04_EleEtaPhi')])} disagreeing events (PC last=Stage00, CMSSW last=Stage04):")
    print(f"  CMSSW leading electron pt < 5 GeV : {n_lt5}")
    print(f"  CMSSW leading electron pt >= 5 GeV: {n_ge5}")
    print(f"  Not found in CMSSW Stage04 tree   : {n_missing}")


if __name__ == "__main__":
    main()
