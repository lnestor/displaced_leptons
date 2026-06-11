"""
Diagnostic for Stage05 (ElePt) disagreements, both directions:

  Direction 1 (PC fails, CMSSW passes):
    For each CMSSW electron surviving all cuts through Stage05 (pt > 45),
    find it in NanoAOD and trace which PC cut removed it.

  Direction 2 (PC passes, CMSSW fails):
    For each NanoAOD electron surviving all cuts through Stage05 (pt > 45),
    find it in MiniAOD and trace which CMSSW cut removed it.

Expected causes:
  ele_pt_correction  -- NanoAOD ECAL energy correction shifts pt across the 45 GeV boundary
  sc_gap_definition  -- matched electron removed by SC gap cut in one framework but not the other
  nano_ele_pt_floor  -- CMSSW keeps a sub-5-GeV electron absent from NanoAOD

Usage:
    python classify_stage5.py <coffea_file> <cmssw_hist_file>
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
GAP_LOW           = 1.4442
GAP_HIGH          = 1.5660
VETO_ETA_MIN      = 0.3
VETO_ETA_MAX      = 1.2
VETO_PHI_MIN      = 0.4
VETO_PHI_MAX      = 0.8
PT_CUT            = 45.0
NANO_ELE_PT_FLOOR = 5.0
MATCH_DR          = 0.05

PC_STAGES = [
    "Stage00_Trigger", "Stage02_EleEta", "Stage03_EleSC", "Stage04_EleEtaPhi",
    "Stage05_ElePt", "Stage06_EleID", "Stage07_EleIso", "Stage08_MuEta",
    "Stage09_MuEtaPhi", "Stage10_MuPt", "Stage11_MuGlobal", "Stage12_MuID",
    "Stage13_MuIso", "Stage14_CosAlpha", "Stage15_DeltaT", "Stage16_DeltaR",
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
    """Load ALL NanoAOD electrons (unfiltered) for target events."""
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
            phi    = float(arr["Electron_phi"][i][j])
            dEtaSC = float(arr["Electron_deltaEtaSC"][i][j])
            etaSC  = abs(eta + dEtaSC)
            eles.append({
                "pt":      float(arr["Electron_pt"][i][j]),
                "eta":     eta,
                "phi":     phi,
                "etaSC":   etaSC,
                "in_gap":  GAP_LOW <= etaSC <= GAP_HIGH,
                "in_veto": VETO_ETA_MIN < eta < VETO_ETA_MAX and
                           VETO_PHI_MIN < phi < VETO_PHI_MAX,
            })
        result[key] = eles
    return result


def load_miniaod(ntuple_file, targets):
    """Load ALL MiniAOD electrons (unfiltered) for target events."""
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
            eles.append({
                "pt":        float(arr["Electron_pt"][i][j]),
                "eta":       eta,
                "phi":       phi,
                "scEta":     float(arr["Electron_scEta"][i][j]),
                "isEBEEGap": bool(arr["Electron_isEBEEGap"][i][j]),
                "in_veto":   VETO_ETA_MIN <= eta <= VETO_ETA_MAX and
                             VETO_PHI_MIN <= phi <= VETO_PHI_MAX,
            })
        result[key] = eles
    return result


def delta_r(e1, e2):
    dphi = abs(e1["phi"] - e2["phi"])
    if dphi > math.pi:
        dphi = 2 * math.pi - dphi
    return math.sqrt((e1["eta"] - e2["eta"])**2 + dphi**2)


def pc_cut_trace(e):
    """First PC cut that removes this electron, or None if all pass."""
    if abs(e["eta"]) >= ETA_CUT:
        return "eta cut (|eta|={:.4f})".format(abs(e["eta"]))
    if e["in_gap"]:
        return "SC gap cut (etaSC={:.5f})".format(e["etaSC"])
    if e["in_veto"]:
        return "eta-phi veto"
    if e["pt"] <= PT_CUT:
        return "pt cut (pt={:.3f})".format(e["pt"])
    return None


def cmssw_cut_trace(e):
    """First CMSSW cut that removes this electron, or None if all pass."""
    if abs(e["eta"]) >= ETA_CUT:
        return "eta cut (|eta|={:.4f})".format(abs(e["eta"]))
    if e["isEBEEGap"]:
        return "SC gap (isEBEEGap=True, scEta={:.5f})".format(e["scEta"])
    if e["in_veto"]:
        return "eta-phi veto"
    if e["pt"] <= PT_CUT:
        return "pt cut (pt={:.3f})".format(e["pt"])
    return None


def reason_from_cut(cut_str):
    if cut_str is None:
        return None
    if "SC gap" in cut_str:
        return "sc_gap_definition"
    if "pt cut" in cut_str:
        return "ele_pt_correction"
    if "eta-phi" in cut_str:
        return "etaphi_veto_definition"
    if "eta cut" in cut_str:
        return "eta_cut"
    return "other"


def analyze_direction(label, events, nano, mini, driving_eles_fn, trace_fn, other_eles_fn):
    """
    For each event, find the 'driving' electrons (those that make one framework
    pass Stage05), then find their counterpart in the other framework and trace
    which cut removes them.

    driving_eles_fn(nano_eles, mini_eles) -> list of electrons causing the pass
    trace_fn(matched_ele) -> cut string (or None if passes all)
    other_eles_fn(nano_eles, mini_eles) -> full collection of the OTHER framework
    """
    classified = {}
    unresolved = []
    missing    = []

    for ev in events:
        nano_eles = nano.get(ev)
        mini_eles = mini.get(ev)

        print("\n  run={} lumi={} event={}".format(ev[0], ev[1], ev[2]))

        if nano_eles is None or mini_eles is None:
            print("    MISSING from files")
            missing.append(ev)
            continue

        driving = driving_eles_fn(nano_eles, mini_eles)
        other   = other_eles_fn(nano_eles, mini_eles)

        print("    {:>7}  {:>8}  {:>8}  note".format("pt", "eta", "phi"))
        for e in driving:
            print("    {:>7.3f}  {:>8.4f}  {:>8.4f}  (driving)".format(
                e["pt"], e["eta"], e["phi"]))
        for e in other:
            print("    {:>7.3f}  {:>8.4f}  {:>8.4f}".format(
                e["pt"], e["eta"], e["phi"]))

        ev_unresolved = False
        ev_reasons = []

        for drv in driving:
            if not other:
                if drv["pt"] < NANO_ELE_PT_FLOOR:
                    ev_reasons.append("nano_ele_pt_floor")
                    print("    -> no match, pt={:.3f} < {} GeV: nano_ele_pt_floor".format(
                        drv["pt"], NANO_ELE_PT_FLOOR))
                else:
                    ev_unresolved = True
                    print("    -> no electrons in other framework: UNRESOLVED")
                continue

            best = min(other, key=lambda e: delta_r(e, drv))
            dr   = delta_r(best, drv)

            if dr > MATCH_DR:
                if drv["pt"] < NANO_ELE_PT_FLOOR:
                    ev_reasons.append("nano_ele_pt_floor")
                    print("    -> driving pt={:.3f} eta={:.4f}: no match (dR={:.3f}), "
                          "pt < 5 GeV: nano_ele_pt_floor".format(
                              drv["pt"], drv["eta"], dr))
                else:
                    ev_unresolved = True
                    print("    -> driving pt={:.3f} eta={:.4f}: no match within "
                          "dR={} (closest dR={:.3f}): UNRESOLVED".format(
                              drv["pt"], drv["eta"], MATCH_DR, dr))
            else:
                cut = trace_fn(best)
                if cut is None:
                    ev_unresolved = True
                    print("    -> driving pt={:.3f} eta={:.4f}: match pt={:.3f} "
                          "dR={:.4f} passes all cuts in other framework: UNRESOLVED".format(
                              drv["pt"], drv["eta"], best["pt"], dr))
                else:
                    reason = reason_from_cut(cut)
                    ev_reasons.append(reason)
                    print("    -> driving pt={:.3f} eta={:.4f}: match pt={:.3f} "
                          "dR={:.4f}, other framework removes at: {}".format(
                              drv["pt"], drv["eta"], best["pt"], dr, cut))

        if ev_unresolved or not ev_reasons:
            unresolved.append(ev)
        else:
            reason = ev_reasons[0]
            classified.setdefault(reason, []).append(ev)

    return classified, unresolved, missing


def passes_stage04_pc(nano_eles):
    return [e for e in nano_eles
            if abs(e["eta"]) < ETA_CUT and not e["in_gap"] and not e["in_veto"]]


def passes_stage04_cmssw(mini_eles):
    return [e for e in mini_eles
            if abs(e["eta"]) < ETA_CUT and not e["isEBEEGap"] and not e["in_veto"]]


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

    # Direction 1: PC fails Stage05, CMSSW passes Stage05
    d1 = sorted(
        (pc_sets.get("Stage04_EleEtaPhi", set()) - pc_sets.get("Stage05_ElePt", set()))
        & cmssw_sets.get("Stage05_ElePt", set())
    )
    # Direction 2: PC passes Stage05, CMSSW entered Stage05 but failed
    d2 = sorted(
        pc_sets.get("Stage05_ElePt", set())
        & (cmssw_sets.get("Stage04_EleEtaPhi", set()) - cmssw_sets.get("Stage05_ElePt", set()))
    )

    all_targets = set(d1) | set(d2)
    print("\n{} events direction 1 (PC fails, CMSSW passes)".format(len(d1)))
    print("{} events direction 2 (PC passes, CMSSW fails)".format(len(d2)))

    print("Loading NanoAOD for target events...")
    nano = load_nano(args.nano_file, all_targets)
    print("Loading MiniAOD ntuple for target events...")
    mini = load_miniaod(args.miniaod_ntuple, all_targets)

    # Direction 1: driving electrons are CMSSW Stage05 passers; trace in NanoAOD
    def d1_driving(nano_eles, mini_eles):
        return [e for e in passes_stage04_cmssw(mini_eles) if e["pt"] > PT_CUT]

    def d1_other(nano_eles, mini_eles):
        return nano_eles  # all NanoAOD electrons, unfiltered

    # Direction 2: driving electrons are NanoAOD Stage05 passers; trace in MiniAOD
    def d2_driving(nano_eles, mini_eles):
        return [e for e in passes_stage04_pc(nano_eles) if e["pt"] > PT_CUT]

    def d2_other(nano_eles, mini_eles):
        return mini_eles  # all MiniAOD electrons, unfiltered

    print("\n" + "=" * 60)
    print("Direction 1: PC fails Stage05, CMSSW passes Stage05")
    print("=" * 60)
    cls1, unres1, miss1 = analyze_direction(
        "D1", d1, nano, mini, d1_driving, pc_cut_trace, d1_other)

    print("\n" + "=" * 60)
    print("Direction 2: PC passes Stage05, CMSSW fails Stage05")
    print("=" * 60)
    cls2, unres2, miss2 = analyze_direction(
        "D2", d2, nano, mini, d2_driving, cmssw_cut_trace, d2_other)

    # Merge results
    all_classified = {}
    for reason, evts in list(cls1.items()) + list(cls2.items()):
        all_classified.setdefault(reason, []).extend(evts)

    print("\n" + "=" * 60)
    print("Summary")
    print("  Direction 1 ({} events):".format(len(d1)))
    for reason, evts in sorted(cls1.items()):
        print("    {}: {}".format(reason, len(evts)))
    print("    Unresolved: {}  Missing: {}".format(len(unres1), len(miss1)))
    print("  Direction 2 ({} events):".format(len(d2)))
    for reason, evts in sorted(cls2.items()):
        print("    {}: {}".format(reason, len(evts)))
    print("    Unresolved: {}  Missing: {}".format(len(unres2), len(miss2)))

    if args.output:
        rows = [(ev, r) for r, evts in all_classified.items() for ev in evts]
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
