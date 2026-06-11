"""
Per-event comparison of PocketCoffea vs CMSSW cutflow.

For every event that passed Stage00 in PocketCoffea:
  - Find the last stage it passed in PC (i.e., appears in stage N but not N+1)
  - Find the last stage it passed in CMSSW (same logic)
  - If they agree: verify kinematics match at that stage
  - If they disagree: flag and scan all CMSSW trees to find where the event
    actually is (in case it's in a stage we wouldn't expect)

Usage:
    python compare_cmssw.py <coffea_file> <cmssw_hist_file>
"""

import sys
import argparse
import csv
import numpy as np
import uproot
from coffea.util import load
from collections import defaultdict

# Ordered stage sequence shared by both frameworks.
# Stage01 (JetBasic) exists in CMSSW but has no PC equivalent -- noted below.
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

# CMSSW TreeMaker key for each PC stage label.
# Stage00TriggerTreeMaker saves ALL events (empty cuts VPSet means no EDFilter runs).
# Stage01JetBasicTreeMaker saves triggered events (trigger IS applied, >=0 jets never cuts).
# So PC Stage00_Trigger maps to Stage01JetBasicTreeMaker.
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

KIN_FIELDS = ["ele_pt", "ele_eta", "mu_pt", "mu_eta"]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_cmssw(hist_file):
    """Return dict[stage_label] -> dict with arrays for run/lumi/event/kinematics."""
    data = {}
    f = uproot.open(hist_file)
    for label, tree_key in CMSSW_TREE.items():
        if tree_key not in f:
            continue
        arr = f[tree_key].arrays(
            ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
             "electron_ptElectron0", "electron_etaElectron0",
             "muon_ptMuon0", "muon_etaMuon0"],
            library="np",
        )
        data[label] = {
            "run":     arr["eventvariable_run"].astype(np.uint32),
            "lumi":    arr["eventvariable_ls"].astype(np.uint32),
            "event":   arr["eventvariable_event"].astype(np.uint64),
            "ele_pt":  arr["electron_ptElectron0"].astype(np.float32),
            "ele_eta": arr["electron_etaElectron0"].astype(np.float32),
            "mu_pt":   arr["muon_ptMuon0"].astype(np.float32),
            "mu_eta":  arr["muon_etaMuon0"].astype(np.float32),
        }
    return data


def load_pc(coffea_file):
    """Return dict[stage_label] -> dict with arrays for run/lumi/event/kinematics."""
    output = load(coffea_file)
    data = {}
    for label, fields in output["stage_events"].items():
        if not fields:
            continue
        data[label] = {f: fields[f].value for f in fields}
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_index(d):
    """Return dict[(run,lumi,event) -> row_index] for fast lookup."""
    return {(int(r), int(l), int(e)): i
            for i, (r, l, e) in enumerate(zip(d["run"], d["lumi"], d["event"]))}


def last_stage_passed(event_id, sets):
    """Return the label of the last stage (highest index) that contains event_id."""
    last = None
    for label in PC_STAGES:
        if label in sets and event_id in sets[label]:
            last = label
    return last


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Per-event comparison of PocketCoffea vs CMSSW cutflow."
    )
    parser.add_argument("coffea_file")
    parser.add_argument("cmssw_hist_file")
    parser.add_argument("--known-reasons", metavar="FILE",
                        help="CSV of known-reason events to exclude from disagreements "
                             "(run,lumi,event,reason); produced by classify_*.py scripts")
    args = parser.parse_args()
    coffea_file, hist_file = args.coffea_file, args.cmssw_hist_file

    known = {}
    if args.known_reasons:
        with open(args.known_reasons, newline='') as f:
            for row in csv.DictReader(f):
                ev = (int(row['run']), int(row['lumi']), int(row['event']))
                known[ev] = row['reason']
        by_reason = defaultdict(int)
        for reason in known.values():
            by_reason[reason] += 1
        print(f"Loaded {len(known)} known-reason events from {args.known_reasons}:")
        for reason, n in sorted(by_reason.items()):
            print(f"  {reason}: {n}")

    print("Loading PocketCoffea output...")
    pc_data = load_pc(coffea_file)
    print("Loading CMSSW output...")
    cmssw_data = load_cmssw(hist_file)

    # Build event sets per stage
    pc_sets    = {label: set(zip(d["run"].tolist(), d["lumi"].tolist(), d["event"].tolist()))
                  for label, d in pc_data.items()}
    cmssw_sets = {label: set(zip(d["run"].tolist(), d["lumi"].tolist(), d["event"].tolist()))
                  for label, d in cmssw_data.items()}

    # Remove known-reason events from all stage sets so they are excluded everywhere:
    # per-stage counts, disagreement loop, and kinematics check.
    if known:
        known_set = set(known.keys())
        for s in pc_sets:
            pc_sets[s] -= known_set
        for s in cmssw_sets:
            cmssw_sets[s] -= known_set

    # Build per-stage row-index maps for kinematics lookup
    pc_idx    = {label: make_index(d) for label, d in pc_data.items()}
    cmssw_idx = {label: make_index(d) for label, d in cmssw_data.items()}

    # All events that entered the PC pipeline (passed Stage00)
    if "Stage00_Trigger" not in pc_sets:
        print("ERROR: Stage00_Trigger not found in PocketCoffea output.")
        sys.exit(1)
    all_events = pc_sets["Stage00_Trigger"]
    print(f"\n{len(all_events)} events passed PC Stage00_Trigger\n")

    agree          = []   # (event_id, stage_label)
    disagree       = []   # (event_id, pc_last, cmssw_last)
    missing_cmssw  = []   # events in PC Stage00 but nowhere in CMSSW

    for ev in sorted(all_events):
        pc_last    = last_stage_passed(ev, pc_sets)
        cmssw_last = last_stage_passed(ev, cmssw_sets)

        if cmssw_last is None:
            missing_cmssw.append(ev)
        elif pc_last == cmssw_last:
            agree.append((ev, pc_last))
        else:
            disagree.append((ev, pc_last, cmssw_last))

    # --- Summary -----------------------------------------------------------
    print(f"{'Agreement':=<60}")
    if known:
        print(f"  Known-reason events excluded:     {len(known)}")
    print(f"  Both agree on last stage passed:  {len(agree)}")
    print(f"  Frameworks disagree:              {len(disagree)}")
    print(f"  In PC Stage00 but absent from all CMSSW stages: {len(missing_cmssw)}")

    # --- Disagree details --------------------------------------------------
    if disagree:
        print(f"\n{'Disagreements':=<60}")
        # Group by (pc_last, cmssw_last)
        groups = defaultdict(list)
        for ev, pl, cl in disagree:
            groups[(pl, cl)].append(ev)
        for (pl, cl), evts in sorted(groups.items()):
            print(f"\n  PC last={pl}  CMSSW last={cl}  ({len(evts)} events)")
            for ev in evts[:5]:
                print(f"    run={ev[0]} lumi={ev[1]} event={ev[2]}")
            if len(evts) > 5:
                print(f"    ... and {len(evts)-5} more")

    # --- Missing from CMSSW ------------------------------------------------
    if missing_cmssw:
        print(f"\n{'In PC Stage00 but not found in any CMSSW stage':=<60}")
        for ev in missing_cmssw[:10]:
            print(f"  run={ev[0]} lumi={ev[1]} event={ev[2]}")
        if len(missing_cmssw) > 10:
            print(f"  ... and {len(missing_cmssw)-10} more")

    # --- Kinematics check for agreeing events ------------------------------
    print(f"\n{'Kinematics check for agreeing events':=<60}")
    max_deltas = {f: 0.0 for f in KIN_FIELDS}
    n_kin = 0
    for ev, stage in agree:
        if stage not in pc_idx or stage not in cmssw_idx:
            continue
        if ev not in pc_idx[stage] or ev not in cmssw_idx[stage]:
            continue
        pi = pc_idx[stage][ev]
        ci = cmssw_idx[stage][ev]
        for f in KIN_FIELDS:
            delta = abs(float(pc_data[stage][f][pi]) - float(cmssw_data[stage][f][ci]))
            if delta > max_deltas[f]:
                max_deltas[f] = delta
        n_kin += 1

    print(f"  Checked {n_kin} events")
    for f in KIN_FIELDS:
        print(f"  {f:8s}  max |PC - CMSSW| = {max_deltas[f]:.5f}")

    # --- Per-stage count summary -------------------------------------------
    print(f"\n{'Per-stage counts':=<60}")
    print(f"  {'Stage':<22} {'CMSSW':>7} {'PC':>7}")
    for label in PC_STAGES:
        nc = len(cmssw_sets.get(label, []))
        np_ = len(pc_sets.get(label, []))
        flag = "" if nc == np_ else "  <-- MISMATCH"
        print(f"  {label:<22} {nc:>7} {np_:>7}{flag}")


if __name__ == "__main__":
    main()
