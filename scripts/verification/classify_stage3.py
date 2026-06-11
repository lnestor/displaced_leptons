"""
Classify Stage03 (EleSC gap veto) disagreements, both directions.

Direction 1 -- PC fails Stage03, CMSSW passes Stage03:
  NanoAOD (PC):    etaSC = |eta + deltaEtaSC|; veto if in [1.4442, 1.5660]
  MiniAOD (CMSSW): veto if isEBEEGap == True
  Expected: electron sits in the gap by PC's numerical etaSC but CMSSW's
  isEBEEGap flag says False -> sc_gap_definition.

Direction 2 -- PC passes Stage03, CMSSW fails Stage03:
  Mirror of Direction 1: PC's etaSC puts the electron outside the gap but
  CMSSW's isEBEEGap=True vetoes it -> sc_gap_definition.

Only electrons that already passed |eta| < 1.5 (Stage02) are relevant.

Usage:
    python classify_stage3.py <coffea_file> <cmssw_hist_file>
           <miniaod_ntuple> <nano_file>
           [--output FILE] [--append]
"""

import sys
import csv
import os
import argparse
import math
import uproot
import awkward as ak
from coffea.util import load

ETA_CUT  = 1.5
GAP_LOW  = 1.4442
GAP_HIGH = 1.5660
REASON   = "sc_gap_definition"
MATCH_DR = 0.05

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
            eles.append({
                "pt":        float(arr["Electron_pt"][i][j]),
                "eta":       eta,
                "phi":       float(arr["Electron_phi"][i][j]),
                "deltaEtaSC": dEtaSC,
                "etaSC":     etaSC,
                "in_gap":    GAP_LOW <= etaSC <= GAP_HIGH,
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
            eles.append({
                "pt":        float(arr["Electron_pt"][i][j]),
                "eta":       float(arr["Electron_eta"][i][j]),
                "phi":       float(arr["Electron_phi"][i][j]),
                "scEta":     float(arr["Electron_scEta"][i][j]),
                "isEBEEGap": bool(arr["Electron_isEBEEGap"][i][j]),
            })
        result[key] = eles
    return result


def delta_r(e1, e2):
    dphi = abs(e1["phi"] - e2["phi"])
    if dphi > math.pi:
        dphi = 2 * math.pi - dphi
    return math.sqrt((e1["eta"] - e2["eta"])**2 + dphi**2)


def print_nano_table(eles):
    print("    {:>7}  {:>8}  {:>10}  {:>8}  {:>8}".format(
        "pt", "eta", "deltaEtaSC", "etaSC", "in_gap"))
    for e in eles:
        print("    {:>7.3f}  {:>8.4f}  {:>10.5f}  {:>8.5f}  {:>8}".format(
            e["pt"], e["eta"], e["deltaEtaSC"], e["etaSC"], str(e["in_gap"])))


def print_mini_table(eles):
    print("    {:>7}  {:>8}  {:>8}  {:>10}".format(
        "pt", "eta", "scEta", "isEBEEGap"))
    for e in eles:
        print("    {:>7.3f}  {:>8.4f}  {:>8.5f}  {:>10}".format(
            e["pt"], e["eta"], e["scEta"], str(e["isEBEEGap"])))


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

    # Direction 1: PC fails Stage03, CMSSW passes Stage03
    d1 = sorted(
        (pc_sets.get("Stage02_EleEta", set()) - pc_sets.get("Stage03_EleSC", set()))
        & cmssw_sets.get("Stage03_EleSC", set())
    )
    # Direction 2: PC passes Stage03, CMSSW entered Stage03 but failed
    d2 = sorted(
        pc_sets.get("Stage03_EleSC", set())
        & (cmssw_sets.get("Stage02_EleEta", set()) - cmssw_sets.get("Stage03_EleSC", set()))
    )

    all_targets = set(d1) | set(d2)
    print("\n{} events direction 1 (PC fails, CMSSW passes)".format(len(d1)))
    print("{} events direction 2 (PC passes, CMSSW fails)".format(len(d2)))

    print("Loading NanoAOD for target events...")
    nano = load_nano(args.nano_file, all_targets)
    print("Loading MiniAOD ntuple for target events...")
    mini = load_miniaod(args.miniaod_ntuple, all_targets)

    # -------------------------------------------------------------------------
    # Direction 1: PC fails Stage03, CMSSW passes Stage03
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Direction 1: PC fails Stage03_EleSC, CMSSW passes Stage03_EleSC")
    print("=" * 60)

    d1_gap_def  = []
    d1_unclear  = []
    d1_missing  = []

    for ev in d1:
        nano_eles = nano.get(ev)
        mini_eles = mini.get(ev)

        print("\nrun={} lumi={} event={}".format(ev[0], ev[1], ev[2]))

        if nano_eles is None or mini_eles is None:
            print("  MISSING")
            d1_missing.append(ev)
            continue

        nano_eta_pass = [e for e in nano_eles if abs(e["eta"]) < ETA_CUT]
        mini_eta_pass = [e for e in mini_eles if abs(e["eta"]) < ETA_CUT]

        print("  NanoAOD ({} total, {} pass |eta|<{}):".format(
            len(nano_eles), len(nano_eta_pass), ETA_CUT))
        print_nano_table(nano_eta_pass)

        print("  MiniAOD ({} total, {} pass |eta|<{}):".format(
            len(mini_eles), len(mini_eta_pass), ETA_CUT))
        print_mini_table(mini_eta_pass)

        pc_keeps    = [e for e in nano_eta_pass if not e["in_gap"]]
        cmssw_keeps = [e for e in mini_eta_pass if not e["isEBEEGap"]]

        print("  PC keeps {}, CMSSW keeps {}".format(len(pc_keeps), len(cmssw_keeps)))

        if len(pc_keeps) == 0 and len(cmssw_keeps) > 0:
            print("  -> {}".format(REASON))
            d1_gap_def.append(ev)
        else:
            print("  -> UNCLEAR")
            d1_unclear.append(ev)

    print("\nDirection 1 summary:")
    print("  {}: {}".format(REASON, len(d1_gap_def)))
    print("  Unclear:  {}".format(len(d1_unclear)))
    print("  Missing:  {}".format(len(d1_missing)))

    # -------------------------------------------------------------------------
    # Direction 2: PC passes Stage03, CMSSW fails Stage03
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Direction 2: PC passes Stage03_EleSC, CMSSW fails Stage03_EleSC")
    print("=" * 60)

    d2_gap_def  = []
    d2_unclear  = []
    d2_missing  = []

    if not d2:
        print("\n  No events in this direction.")
    else:
        for ev in d2:
            nano_eles = nano.get(ev)
            mini_eles = mini.get(ev)

            print("\nrun={} lumi={} event={}".format(ev[0], ev[1], ev[2]))

            if nano_eles is None or mini_eles is None:
                print("  MISSING")
                d2_missing.append(ev)
                continue

            nano_eta_pass = [e for e in nano_eles if abs(e["eta"]) < ETA_CUT]
            mini_eta_pass = [e for e in mini_eles if abs(e["eta"]) < ETA_CUT]

            print("  NanoAOD ({} total, {} pass |eta|<{}):".format(
                len(nano_eles), len(nano_eta_pass), ETA_CUT))
            print_nano_table(nano_eta_pass)

            print("  MiniAOD ({} total, {} pass |eta|<{}):".format(
                len(mini_eles), len(mini_eta_pass), ETA_CUT))
            print_mini_table(mini_eta_pass)

            pc_keeps    = [e for e in nano_eta_pass if not e["in_gap"]]
            cmssw_keeps = [e for e in mini_eta_pass if not e["isEBEEGap"]]

            print("  PC keeps {}, CMSSW keeps {}".format(len(pc_keeps), len(cmssw_keeps)))

            if len(pc_keeps) > 0 and len(cmssw_keeps) == 0:
                # Verify the PC-passing electron has a MiniAOD counterpart with isEBEEGap=True
                confirmed = False
                for pc_e in pc_keeps:
                    if not mini_eta_pass:
                        break
                    best = min(mini_eta_pass, key=lambda e: delta_r(e, pc_e))
                    dr = delta_r(best, pc_e)
                    if dr < MATCH_DR and best["isEBEEGap"]:
                        print("  -> {}: PC keeps electron at etaSC={:.5f}, "
                              "MiniAOD match (dR={:.4f}) has isEBEEGap=True "
                              "(scEta={:.5f})".format(
                                  REASON, pc_e["etaSC"], dr, best["scEta"]))
                        confirmed = True
                        break
                if confirmed:
                    d2_gap_def.append(ev)
                else:
                    print("  -> UNCLEAR (no dR match for PC-passing electron)")
                    d2_unclear.append(ev)
            else:
                print("  -> UNCLEAR")
                d2_unclear.append(ev)

        print("\nDirection 2 summary:")
        print("  {}: {}".format(REASON, len(d2_gap_def)))
        print("  Unclear:  {}".format(len(d2_unclear)))
        print("  Missing:  {}".format(len(d2_missing)))

    # -------------------------------------------------------------------------
    # Write CSV
    # -------------------------------------------------------------------------
    if args.output:
        rows = [(ev, REASON) for ev in d1_gap_def + d2_gap_def]
        if rows:
            write_header = not (args.append and os.path.exists(args.output))
            mode = "a" if args.append else "w"
            with open(args.output, mode, newline="") as fout:
                writer = csv.writer(fout)
                if write_header:
                    writer.writerow(["run", "lumi", "event", "reason"])
                for ev, reason in rows:
                    writer.writerow([ev[0], ev[1], ev[2], reason])
            print("\nWrote {} events to {}".format(len(rows), args.output))


if __name__ == "__main__":
    main()
