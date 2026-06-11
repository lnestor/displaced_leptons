"""
Classify Stage02 (EleEta) disagreements, both directions.

Direction 1 -- PC fails Stage02, CMSSW passes Stage02:
  Look at MiniAOD electrons passing |eta| < 1.5. If ALL have pt < 5 GeV,
  NanoAOD never stored them -> nano_ele_pt_floor. If any has pt >= 5 GeV
  -> unresolved.

Direction 2 -- PC passes Stage02, CMSSW fails Stage02:
  Look at NanoAOD electrons passing |eta| < 1.5 (what PC uses to pass),
  then find the same electrons in MiniAOD and report their eta values.
  CMSSW fails because no MiniAOD electron passes |eta| < 1.5.

Usage:
    python classify_stage2.py <coffea_file> <cmssw_hist_file>
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

ETA_CUT           = 1.5
NANO_ELE_PT_FLOOR = 5.0
MATCH_DR          = 0.05

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


def load_miniaod(ntuple_file, targets):
    """Load ALL MiniAOD electrons for target events."""
    f = uproot.open(ntuple_file)
    arr = f["Events"].arrays(
        ["run", "lumi", "event", "Electron_pt", "Electron_eta", "Electron_phi"],
        library="ak",
    )
    result = {}
    for i in range(len(arr)):
        key = (int(arr["run"][i]), int(arr["lumi"][i]), int(arr["event"][i]))
        if key not in targets:
            continue
        result[key] = [
            {"pt": float(arr["Electron_pt"][i][j]),
             "eta": float(arr["Electron_eta"][i][j]),
             "phi": float(arr["Electron_phi"][i][j])}
            for j in range(len(arr["Electron_pt"][i]))
        ]
    return result


def load_nano(nano_file, targets):
    """Load ALL NanoAOD electrons for target events."""
    f = uproot.open(nano_file)
    arr = f["Events"].arrays(
        ["run", "luminosityBlock", "event",
         "Electron_pt", "Electron_eta", "Electron_phi"],
        library="ak",
    )
    result = {}
    for i in range(len(arr)):
        key = (int(arr["run"][i]), int(arr["luminosityBlock"][i]), int(arr["event"][i]))
        if key not in targets:
            continue
        result[key] = [
            {"pt": float(arr["Electron_pt"][i][j]),
             "eta": float(arr["Electron_eta"][i][j]),
             "phi": float(arr["Electron_phi"][i][j])}
            for j in range(len(arr["Electron_pt"][i]))
        ]
    return result


def delta_r(e1, e2):
    dphi = abs(e1["phi"] - e2["phi"])
    if dphi > math.pi:
        dphi = 2 * math.pi - dphi
    return math.sqrt((e1["eta"] - e2["eta"])**2 + dphi**2)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("coffea_file")
    parser.add_argument("cmssw_hist_file")
    parser.add_argument("miniaod_ntuple")
    parser.add_argument("nano_file")
    parser.add_argument("--output", metavar="FILE",
                        help="CSV to write confirmed events to; if omitted, only prints")
    parser.add_argument("--append", action="store_true",
                        help="Append to output file instead of overwriting")
    args = parser.parse_args()

    print("Loading PocketCoffea output...")
    pc_sets = load_pc_sets(args.coffea_file)
    print("Loading CMSSW output...")
    cmssw_sets = load_cmssw_sets(args.cmssw_hist_file)

    if "Stage00_Trigger" not in pc_sets:
        print("ERROR: Stage00_Trigger not found in PocketCoffea output.")
        sys.exit(1)

    # Direction 1: PC fails Stage02, CMSSW passes Stage02
    d1 = sorted(
        (pc_sets["Stage00_Trigger"] - pc_sets.get("Stage02_EleEta", set()))
        & cmssw_sets.get("Stage02_EleEta", set())
    )
    # Direction 2: PC passes Stage02, CMSSW entered Stage02 but failed
    d2 = sorted(
        pc_sets.get("Stage02_EleEta", set())
        & (cmssw_sets.get("Stage00_Trigger", set()) - cmssw_sets.get("Stage02_EleEta", set()))
    )

    all_targets = set(d1) | set(d2)
    print("\n{} events direction 1 (PC fails, CMSSW passes)".format(len(d1)))
    print("{} events direction 2 (PC passes, CMSSW fails)".format(len(d2)))

    print("Loading MiniAOD ntuple for target events...")
    mini = load_miniaod(args.miniaod_ntuple, all_targets)
    print("Loading NanoAOD for target events...")
    nano = load_nano(args.nano_file, all_targets)

    # -------------------------------------------------------------------------
    # Direction 1
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Direction 1: PC fails Stage02_EleEta, CMSSW passes Stage02_EleEta")
    print("=" * 60)

    d1_confirmed   = []
    d1_unresolved  = []
    d1_no_eta_pass = []
    d1_missing     = []

    for ev in d1:
        entry = mini.get(ev)
        if entry is None:
            d1_missing.append(ev)
            continue

        # MiniAOD electrons passing the eta cut -- these are what CMSSW uses
        passing = [e for e in entry if abs(e["eta"]) < ETA_CUT]

        if not passing:
            d1_no_eta_pass.append(ev)
        elif all(e["pt"] < NANO_ELE_PT_FLOOR for e in passing):
            d1_confirmed.append((ev, [e["pt"] for e in passing]))
        else:
            d1_unresolved.append((ev, [e["pt"] for e in passing]))

    print("\nResults:")
    print("  nano_ele_pt_floor: {}".format(len(d1_confirmed)))
    print("  Unresolved (>=5 GeV ele passing eta cut): {}".format(len(d1_unresolved)))
    print("  No MiniAOD electron passes eta cut: {}".format(len(d1_no_eta_pass)))
    print("  Missing from ntuple: {}".format(len(d1_missing)))

    if d1_confirmed:
        pts_all = [pt for _, pts in d1_confirmed for pt in pts]
        print("  Confirmed pt range: min={:.3f}  max={:.3f}  n_eles={}".format(
            min(pts_all), max(pts_all), len(pts_all)))

    if d1_unresolved:
        print("\n  Unresolved events (first 10):")
        for ev, pts in d1_unresolved[:10]:
            print("    run={} lumi={} event={}  mini eta-passing pts: {}".format(
                ev[0], ev[1], ev[2], ["{:.2f}".format(p) for p in sorted(pts)]))
        if len(d1_unresolved) > 10:
            print("    ... and {} more".format(len(d1_unresolved) - 10))

    if d1_no_eta_pass:
        print("\n  No-eta-pass events (first 5):")
        for ev in d1_no_eta_pass[:5]:
            entry = mini[ev]
            print("    run={} lumi={} event={}  all mini etas: {}".format(
                ev[0], ev[1], ev[2],
                ["{:.3f}".format(e["eta"]) for e in entry]))

    # -------------------------------------------------------------------------
    # Direction 2
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Direction 2: PC passes Stage02_EleEta, CMSSW fails Stage02_EleEta")
    print("=" * 60)

    if not d2:
        print("\n  No events in this direction.")
    else:
        d2_eta_diff   = []   # NanoAOD electron near eta boundary, MiniAOD counterpart outside
        d2_unresolved = []
        d2_missing    = []

        for ev in d2:
            nano_eles = nano.get(ev)
            mini_eles = mini.get(ev)

            print("\n  run={} lumi={} event={}".format(ev[0], ev[1], ev[2]))

            if nano_eles is None or mini_eles is None:
                print("    MISSING: nano={} mini={}".format(
                    nano_eles is not None, mini_eles is not None))
                d2_missing.append(ev)
                continue

            # NanoAOD electrons passing eta -- these make PC pass Stage02
            nano_pass = [e for e in nano_eles if abs(e["eta"]) < ETA_CUT]

            print("  NanoAOD ({} total, {} pass |eta|<{}):".format(
                len(nano_eles), len(nano_pass), ETA_CUT))
            print("    {:>7}  {:>8}  {:>8}".format("pt", "eta", "phi"))
            for e in nano_pass:
                print("    {:>7.3f}  {:>8.4f}  {:>8.4f}".format(
                    e["pt"], e["eta"], e["phi"]))

            print("  MiniAOD ({} total, 0 pass |eta|<{}):".format(
                len(mini_eles), ETA_CUT))
            print("    {:>7}  {:>8}  {:>8}  {:>12}".format(
                "pt", "eta", "phi", "nano_match_eta"))
            for mini_e in mini_eles:
                # Find nearest NanoAOD electron to show the eta difference
                if nano_eles:
                    best = min(nano_eles, key=lambda e: delta_r(e, mini_e))
                    dr   = delta_r(best, mini_e)
                    match_info = "{:.4f} (dR={:.3f})".format(
                        best["eta"], dr) if dr < MATCH_DR else "no match"
                else:
                    match_info = "no nano eles"
                print("    {:>7.3f}  {:>8.4f}  {:>8.4f}  {:>12}".format(
                    mini_e["pt"], mini_e["eta"], mini_e["phi"], match_info))

            # Classify: for each NanoAOD electron passing eta,
            # find its MiniAOD counterpart and check its eta
            ev_resolved = False
            for nano_e in nano_pass:
                if not mini_eles:
                    break
                best_mini = min(mini_eles, key=lambda e: delta_r(e, nano_e))
                dr = delta_r(best_mini, nano_e)
                if dr < MATCH_DR and abs(best_mini["eta"]) >= ETA_CUT:
                    print("  -> eta measurement difference: "
                          "nano |eta|={:.4f} < {}, mini |eta|={:.4f} >= {}".format(
                              abs(nano_e["eta"]), ETA_CUT,
                              abs(best_mini["eta"]), ETA_CUT))
                    d2_eta_diff.append(ev)
                    ev_resolved = True
                    break

            if not ev_resolved:
                print("  -> UNRESOLVED")
                d2_unresolved.append(ev)

        print("\nResults:")
        print("  eta_measurement_diff: {}".format(len(d2_eta_diff)))
        print("  Unresolved:           {}".format(len(d2_unresolved)))
        print("  Missing:              {}".format(len(d2_missing)))

    # -------------------------------------------------------------------------
    # Write CSV
    # -------------------------------------------------------------------------
    if args.output:
        rows = [(ev, "nano_ele_pt_floor") for ev, _ in d1_confirmed]
        if d2:
            rows += [(ev, "eta_measurement_diff") for ev in d2_eta_diff]
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
