"""
Diagnostic for Stage04 (EleEtaPhi veto) disagreements.

Finds events where PC fails Stage04_EleEtaPhi but CMSSW passes Stage04_EleEtaPhi,
then prints electron eta and phi from both NanoAOD (PC) and MiniAOD (CMSSW).

Veto region (2018 pixel power supply):
  PC (exclusive):   eta in (0.3, 1.2)  AND  phi in (0.4, 0.8)
  CMSSW (inclusive): eta in [0.3, 1.2]  AND  phi in [0.4, 0.8]

Only electrons surviving the cumulative cuts up to Stage03 are relevant,
so we pre-filter by |eta| < 1.5 and not in the SC gap (pc_etaSC in [1.4442, 1.5660]).

Usage:
    python classify_stage4.py <coffea_file> <cmssw_hist_file>
           <miniaod_ntuple> <nano_file>
"""

import sys
import csv
import os
import argparse
import uproot
import awkward as ak
from coffea.util import load

ETA_CUT          = 1.5
GAP_LOW          = 1.4442
GAP_HIGH         = 1.5660
NANO_ELE_PT_FLOOR = 5.0

# 2018 eta-phi veto region
VETO_ETA_MIN = 0.3
VETO_ETA_MAX = 1.2
VETO_PHI_MIN = 0.4
VETO_PHI_MAX = 0.8

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


def load_pc_sets(coffea_file):
    output = load(coffea_file)
    sets = {}
    for label, fields in output["stage_events"].items():
        if not fields:
            continue
        d = {f: fields[f].value for f in fields}
        sets[label] = set(zip(d["run"].tolist(), d["lumi"].tolist(), d["event"].tolist()))
    return sets


def load_cmssw_sets(hist_file):
    f = uproot.open(hist_file)
    sets = {}
    for label, tree_key in CMSSW_TREE.items():
        if tree_key not in f:
            continue
        arr = f[tree_key].arrays(
            ["eventvariable_run", "eventvariable_ls", "eventvariable_event"],
            library="np",
        )
        ids = list(zip(
            arr["eventvariable_run"].astype(int).tolist(),
            arr["eventvariable_ls"].astype(int).tolist(),
            arr["eventvariable_event"].astype(int).tolist(),
        ))
        sets[label] = set(ids)
    return sets


def load_nano(nano_file, targets):
    f = uproot.open(nano_file)
    arr = f["Events"].arrays(
        ["run", "luminosityBlock", "event",
         "Electron_pt", "Electron_eta", "Electron_phi", "Electron_deltaEtaSC"],
        library="ak",
    )
    result = {}
    for i in range(len(arr)):
        key = (int(arr["run"][i]), int(arr["luminosityBlock"][i]), int(arr["event"][i]))
        if key not in targets:
            continue
        eles = []
        for j in range(len(arr["Electron_pt"][i])):
            eta    = float(arr["Electron_eta"][i][j])
            dEtaSC = float(arr["Electron_deltaEtaSC"][i][j])
            etaSC  = abs(eta + dEtaSC)
            in_gap = GAP_LOW <= etaSC <= GAP_HIGH
            in_veto_pc = (
                VETO_ETA_MIN < eta < VETO_ETA_MAX and
                VETO_PHI_MIN < float(arr["Electron_phi"][i][j]) < VETO_PHI_MAX
            )
            eles.append({
                "pt":       float(arr["Electron_pt"][i][j]),
                "eta":      eta,
                "phi":      float(arr["Electron_phi"][i][j]),
                "etaSC":    etaSC,
                "in_gap":   in_gap,
                "in_veto":  in_veto_pc,
            })
        result[key] = eles
    return result


def load_miniaod(ntuple_file, targets):
    f = uproot.open(ntuple_file)
    arr = f["Events"].arrays(
        ["run", "lumi", "event",
         "Electron_pt", "Electron_eta", "Electron_phi",
         "Electron_scEta", "Electron_isEBEEGap"],
        library="ak",
    )
    result = {}
    for i in range(len(arr)):
        key = (int(arr["run"][i]), int(arr["lumi"][i]), int(arr["event"][i]))
        if key not in targets:
            continue
        eles = []
        for j in range(len(arr["Electron_pt"][i])):
            eta = float(arr["Electron_eta"][i][j])
            phi = float(arr["Electron_phi"][i][j])
            in_veto_cmssw = (
                VETO_ETA_MIN <= eta <= VETO_ETA_MAX and
                VETO_PHI_MIN <= phi <= VETO_PHI_MAX
            )
            eles.append({
                "pt":        float(arr["Electron_pt"][i][j]),
                "eta":       eta,
                "phi":       phi,
                "scEta":     float(arr["Electron_scEta"][i][j]),
                "isEBEEGap": bool(arr["Electron_isEBEEGap"][i][j]),
                "in_veto":   in_veto_cmssw,
            })
        result[key] = eles
    return result


def passes_stage03_pc(e):
    return abs(e["eta"]) < ETA_CUT and not e["in_gap"]


def passes_stage03_cmssw(e):
    return abs(e["eta"]) < ETA_CUT and not e["isEBEEGap"]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("coffea_file")
    parser.add_argument("cmssw_hist_file")
    parser.add_argument("miniaod_ntuple")
    parser.add_argument("nano_file")
    parser.add_argument("--output", metavar="FILE",
                        help="CSV to write classified events to; if omitted, only prints")
    parser.add_argument("--append", action="store_true",
                        help="Append to output file instead of overwriting")
    args = parser.parse_args()

    print("Loading PocketCoffea output...")
    pc_sets = load_pc_sets(args.coffea_file)
    print("Loading CMSSW output...")
    cmssw_sets = load_cmssw_sets(args.cmssw_hist_file)

    # Events passing Stage03 in PC but failing Stage04, while CMSSW passes Stage04
    pc_fail    = pc_sets.get("Stage03_EleSC", set()) - pc_sets.get("Stage04_EleEtaPhi", set())
    cmssw_pass = cmssw_sets.get("Stage04_EleEtaPhi", set())
    disagree   = sorted(pc_fail & cmssw_pass)

    print("\n{} events: PC fails Stage04_EleEtaPhi, CMSSW passes Stage04_EleEtaPhi".format(
        len(disagree)))
    print("Veto region: eta in ({},{}) phi in ({},{})".format(
        VETO_ETA_MIN, VETO_ETA_MAX, VETO_PHI_MIN, VETO_PHI_MAX))

    targets = set(disagree)
    print("Loading NanoAOD for target events...")
    nano = load_nano(args.nano_file, targets)
    print("Loading MiniAOD ntuple for target events...")
    mini = load_miniaod(args.miniaod_ntuple, targets)

    cat_pt_floor = []
    cat_unresolved = []
    cat_missing = []

    for ev in disagree:
        nano_eles = nano.get(ev)
        mini_eles = mini.get(ev)

        print("\nrun={} lumi={} event={}".format(ev[0], ev[1], ev[2]))

        if nano_eles is None or mini_eles is None:
            print("  MISSING: nano={} mini={}".format(
                nano_eles is not None, mini_eles is not None))
            cat_missing.append(ev)
            continue

        # Pre-filter to electrons that survived Stage03 in each framework
        nano_survive = [e for e in nano_eles if passes_stage03_pc(e)]
        mini_survive = [e for e in mini_eles if passes_stage03_cmssw(e)]

        print("  NanoAOD (PC): {} survive Stage03, {} in veto region".format(
            len(nano_survive), sum(e["in_veto"] for e in nano_survive)))
        print("    {:>7}  {:>8}  {:>8}  {:>10}".format("pt", "eta", "phi", "PC_vetoed"))
        for e in nano_survive:
            print("    {:>7.3f}  {:>8.4f}  {:>8.4f}  {:>10}".format(
                e["pt"], e["eta"], e["phi"], str(e["in_veto"])))

        print("  MiniAOD (CMSSW): {} survive Stage03, {} in veto region".format(
            len(mini_survive), sum(e["in_veto"] for e in mini_survive)))
        print("    {:>7}  {:>8}  {:>8}  {:>13}".format("pt", "eta", "phi", "CMSSW_vetoed"))
        for e in mini_survive:
            print("    {:>7.3f}  {:>8.4f}  {:>8.4f}  {:>13}".format(
                e["pt"], e["eta"], e["phi"], str(e["in_veto"])))

        # Classification: PC keeps 0 electrons after veto; check why CMSSW keeps any.
        # If all electrons CMSSW keeps (not in veto) have pt < 5 GeV, NanoAOD never
        # stored them -- nano_ele_pt_floor explains the disagreement.
        pc_keeps    = [e for e in nano_survive if not e["in_veto"]]
        cmssw_keeps = [e for e in mini_survive if not e["in_veto"]]

        if len(pc_keeps) == 0 and len(cmssw_keeps) > 0:
            if all(e["pt"] < NANO_ELE_PT_FLOOR for e in cmssw_keeps):
                print("  -> nano_ele_pt_floor: CMSSW keeps {} sub-5-GeV electron(s) "
                      "absent from NanoAOD".format(len(cmssw_keeps)))
                cat_pt_floor.append(ev)
            else:
                print("  -> UNRESOLVED: CMSSW keeps electron(s) with pt >= 5 GeV "
                      "that PC does not")
                cat_unresolved.append(ev)
        else:
            print("  -> UNRESOLVED: pc_keeps={} cmssw_keeps={}".format(
                len(pc_keeps), len(cmssw_keeps)))
            cat_unresolved.append(ev)

    print("\n" + "=" * 60)
    print("Summary: {} disagreeing events".format(len(disagree)))
    print("  nano_ele_pt_floor: {}".format(len(cat_pt_floor)))
    print("  Unresolved:        {}".format(len(cat_unresolved)))
    print("  Missing:           {}".format(len(cat_missing)))

    if args.output and cat_pt_floor:
        write_header = not (args.append and os.path.exists(args.output))
        mode = "a" if args.append else "w"
        with open(args.output, mode, newline="") as fout:
            writer = csv.writer(fout)
            if write_header:
                writer.writerow(["run", "lumi", "event", "reason"])
            for ev in cat_pt_floor:
                writer.writerow([ev[0], ev[1], ev[2], "nano_ele_pt_floor"])
        print("\nWrote {} events to {}".format(len(cat_pt_floor), args.output))


if __name__ == "__main__":
    main()
