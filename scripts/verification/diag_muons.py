"""
Diagnostic for post-Stage07 muon disagreements.

Groups investigated:
  G1: PC last=Stage07_EleIso, CMSSW last=Stage09_MuEtaPhi (5 events)
      Hypothesis: CMSSW leading muon has pt < 3 GeV (NanoAOD muon floor),
                  so the muon is absent from NanoAOD and PC finds none passing eta.

  G2: PC last=Stage11_MuGlobal, CMSSW last=Stage10_MuPt (1 event)
      Hypothesis: CMSSW Stage11 requires isGlobalMuon AND isPFMuon;
                  PocketCoffea only checks isGlobal.

  G3: PC last=Stage17_NoDispVtx, CMSSW last=Stage14_CosAlpha (1 event)
      PC passes all stages but CMSSW fails Stage15_DeltaT.
      (Stage15 and Stage16 agree overall; this event is offset by the
       PC=Stage17/CMSSW=Stage14 case elsewhere.)

Usage:
    python diag_muons.py <coffea_file> <cmssw_hist_file> <nano_file>
"""

import sys
import numpy as np
import uproot
import awkward as ak
from coffea.util import load

PC_STAGES = [
    "Stage00_Trigger",
    "Stage02_EleEta", "Stage03_EleSC", "Stage04_EleEtaPhi",
    "Stage05_ElePt",  "Stage06_EleID",  "Stage07_EleIso",
    "Stage08_MuEta",  "Stage09_MuEtaPhi", "Stage10_MuPt",
    "Stage11_MuGlobal", "Stage12_MuID", "Stage13_MuIso",
    "Stage14_CosAlpha", "Stage15_DeltaT", "Stage16_DeltaR",
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

# 2018 analysis cuts
MU_ETA      = 1.5
MU_PT       = 45.0
MU_VETO     = dict(eta_min=0.3, eta_max=1.2, phi_min=0.4, phi_max=0.8)
MU_ISO      = 0.10
NANO_MU_MIN = 3.0   # NanoAOD muon pt floor in CMSSW_10_2_22


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def last_stage_passed(ev, sets):
    last = None
    for label in PC_STAGES:
        if label in sets and ev in sets[label]:
            last = label
    return last


def load_pc_sets(coffea_file):
    output = load(coffea_file)
    sets = {}
    for label, fields in output["stage_events"].items():
        if not fields:
            continue
        d = {f: fields[f].value for f in fields}
        sets[label] = set(zip(d["run"].tolist(), d["lumi"].tolist(), d["event"].tolist()))
    return sets


def load_cmssw(hist_file, target_stages):
    """Return (sets, mu_kin) for requested stages.

    mu_kin[stage][event_id] = dict with 'pt', 'eta' (and 'phi' if present).
    """
    f = uproot.open(hist_file)
    sets    = {}
    mu_kin  = {}
    for label in target_stages:
        tree_key = CMSSW_TREE.get(label)
        if not tree_key or tree_key not in f:
            continue
        tree = f[tree_key]
        want = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
                "muon_ptMuon0", "muon_etaMuon0", "muon_phiMuon0"]
        avail = [b for b in want if b in tree.keys()]
        arr = tree.arrays(avail, library="np")
        ids = list(zip(
            arr["eventvariable_run"].astype(int).tolist(),
            arr["eventvariable_ls"].astype(int).tolist(),
            arr["eventvariable_event"].astype(int).tolist(),
        ))
        sets[label] = set(ids)
        mu_kin[label] = {}
        for i, ev in enumerate(ids):
            entry = {}
            for src, dst in [("muon_ptMuon0", "pt"), ("muon_etaMuon0", "eta"), ("muon_phiMuon0", "phi")]:
                if src in arr:
                    entry[dst] = float(arr[src][i])
            mu_kin[label][ev] = entry
    return sets, mu_kin


def load_nano_muons(nano_file, targets):
    """Return dict[event_id] -> list of per-muon dicts with cut masks."""
    nano = uproot.open(nano_file)["Events"]
    want = ["run", "luminosityBlock", "event",
            "Muon_pt", "Muon_eta", "Muon_phi",
            "Muon_isGlobal", "Muon_isPFcand",
            "Muon_tightId", "Muon_mediumId",
            "Muon_pfRelIso04_all", "Muon_customIso"]
    avail = [b for b in want if b in nano.keys()]
    arrays = nano.arrays(avail, library="ak")

    result = {}
    for i in range(len(arrays)):
        ev = (int(arrays["run"][i]),
              int(arrays["luminosityBlock"][i]),
              int(arrays["event"][i]))
        if ev not in targets:
            continue
        muons = []
        n = len(arrays["Muon_pt"][i])
        for j in range(n):
            pt  = float(arrays["Muon_pt"][i][j])
            eta = float(arrays["Muon_eta"][i][j])
            phi = float(arrays["Muon_phi"][i][j]) if "Muon_phi" in avail else float("nan")
            m = {"pt": pt, "eta": eta, "phi": phi}
            for field in ["Muon_isGlobal", "Muon_isPFcand",
                          "Muon_tightId", "Muon_mediumId",
                          "Muon_pfRelIso04_all", "Muon_customIso"]:
                if field in avail:
                    key = field.replace("Muon_", "")
                    val = arrays[field][i][j]
                    m[key] = bool(val) if field in ("Muon_isGlobal", "Muon_isPFcand",
                                                     "Muon_tightId", "Muon_mediumId") else float(val)
            # Cut masks
            in_veto_strict = (
                (eta > MU_VETO["eta_min"]) and (eta < MU_VETO["eta_max"]) and
                (phi > MU_VETO["phi_min"]) and (phi < MU_VETO["phi_max"])
            )
            in_veto_incl = (
                (eta >= MU_VETO["eta_min"]) and (eta <= MU_VETO["eta_max"]) and
                (phi >= MU_VETO["phi_min"]) and (phi <= MU_VETO["phi_max"])
            )
            m["pass_eta"]         = abs(eta) < MU_ETA
            m["pass_veto_pc"]     = not in_veto_strict   # PC uses strict (<, >)
            m["pass_veto_cmssw"]  = not in_veto_incl     # CMSSW uses inclusive (<=, >=)
            m["pass_pt"]          = pt > MU_PT
            m["above_nano_min"]   = pt > NANO_MU_MIN
            muons.append(m)
        result[ev] = muons
    return result


# ---------------------------------------------------------------------------
# Printers
# ---------------------------------------------------------------------------

def print_nano_muons(muons, show_id=True, show_iso=True):
    if not muons:
        print("    (no muons in NanoAOD)")
        return
    hdr = f"    {'i':>2}  {'pt':>8}  {'eta':>7}  {'phi':>7}"
    if show_id:
        hdr += f"  {'isGlob':>7}  {'isPF':>6}  {'tightId':>8}  {'medId':>6}"
    if show_iso:
        hdr += f"  {'pfIso04':>8}  {'custIso':>8}"
    hdr += f"  {'eta<1.5':>7}  {'!vPC':>5}  {'!vCMS':>6}  {'pt>45':>6}  {'>3GeV':>6}"
    print(hdr)
    for j, m in enumerate(muons):
        row = f"    {j:>2}  {m['pt']:>8.3f}  {m['eta']:>7.4f}  {m['phi']:>7.4f}"
        if show_id:
            for key in ["isGlobal", "isPFcand", "tightId", "mediumId"]:
                row += f"  {str(m.get(key, '?')):>7}"
        if show_iso:
            for key in ["pfRelIso04_all", "customIso"]:
                val = m.get(key)
                row += f"  {val:>8.4f}" if val is not None else f"  {'n/a':>8}"
        row += (f"  {str(m['pass_eta']):>7}"
                f"  {str(m['pass_veto_pc']):>5}"
                f"  {str(m['pass_veto_cmssw']):>6}"
                f"  {str(m['pass_pt']):>6}"
                f"  {str(m['above_nano_min']):>6}")
        print(row)


def print_cmssw_mu(ev, mu_kin, stages):
    print(f"  CMSSW muon0 per stage:")
    print(f"    {'stage':<22}  {'in tree':>7}  {'pt':>8}  {'eta':>8}  {'phi':>8}")
    for stage in stages:
        if ev in mu_kin.get(stage, {}):
            d = mu_kin[stage][ev]
            pt  = d.get("pt",  float("nan"))
            eta = d.get("eta", float("nan"))
            phi = d.get("phi", float("nan"))
            print(f"    {stage:<22}  {'yes':>7}  {pt:>8.3f}  {eta:>8.4f}  {phi:>8.4f}")
        else:
            print(f"    {stage:<22}  {'no':>7}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print("Usage: python diag_muons.py <coffea_file> <cmssw_hist_file> <nano_file>")
        sys.exit(1)
    coffea_file, hist_file, nano_file = sys.argv[1], sys.argv[2], sys.argv[3]

    print("Loading PocketCoffea output...")
    pc_sets = load_pc_sets(coffea_file)

    g1_stages = ["Stage08_MuEta", "Stage09_MuEtaPhi"]
    g2_stages = ["Stage10_MuPt", "Stage11_MuGlobal"]
    g3_stages = ["Stage13_MuIso", "Stage14_CosAlpha", "Stage15_DeltaT"]
    all_stages = g1_stages + g2_stages + g3_stages

    print("Loading CMSSW output...")
    cmssw_sets, mu_kin = load_cmssw(hist_file, all_stages)

    all_events = pc_sets.get("Stage00_Trigger", set())
    groups = {"G1": [], "G2": [], "G3": []}
    for ev in sorted(all_events):
        pc_last    = last_stage_passed(ev, pc_sets)
        cmssw_last = last_stage_passed(ev, cmssw_sets)
        if pc_last == "Stage07_EleIso"  and cmssw_last == "Stage09_MuEtaPhi":
            groups["G1"].append(ev)
        elif pc_last == "Stage11_MuGlobal" and cmssw_last == "Stage10_MuPt":
            groups["G2"].append(ev)
        elif pc_last == "Stage17_NoDispVtx" and cmssw_last == "Stage14_CosAlpha":
            groups["G3"].append(ev)

    all_targets = {ev for evts in groups.values() for ev in evts}
    print("Loading NanoAOD muons...")
    nano_mu = load_nano_muons(nano_file, all_targets)

    # -----------------------------------------------------------------------
    # G1: PC=Stage07, CMSSW=Stage09
    # -----------------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"  G1: PC=Stage07_EleIso, CMSSW=Stage09_MuEtaPhi  ({len(groups['G1'])} events)")
    print(f"  Hypothesis: CMSSW muon pt < {NANO_MU_MIN} GeV  ->  absent from NanoAOD")
    print(f"              PC finds no muon passing eta; CMSSW passes Stage08-09")
    print(f"              then fails Stage10_MuPt (pt < 45) -- same pattern as ele pt < 5")
    print(f"{'='*72}")
    for ev in groups["G1"]:
        print(f"\n  run={ev[0]}  lumi={ev[1]}  event={ev[2]}")
        muons = nano_mu.get(ev, [])
        print(f"  NanoAOD muons ({len(muons)} total):")
        print_nano_muons(muons, show_id=False, show_iso=False)
        print_cmssw_mu(ev, mu_kin, g1_stages)
        pt = mu_kin.get("Stage08_MuEta", {}).get(ev, {}).get("pt")
        if pt is not None:
            verdict = (f"pt={pt:.3f} < {NANO_MU_MIN} GeV  -> NanoAOD floor confirmed"
                       if pt < NANO_MU_MIN else
                       f"pt={pt:.3f} >= {NANO_MU_MIN} GeV  -> NOT explained by pt floor")
            print(f"  --> CMSSW muon0 {verdict}")

    # -----------------------------------------------------------------------
    # G2: PC=Stage11, CMSSW=Stage10
    # -----------------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"  G2: PC=Stage11_MuGlobal, CMSSW=Stage10_MuPt  ({len(groups['G2'])} events)")
    print(f"  Hypothesis: CMSSW Stage11 requires isGlobalMuon AND isPFMuon;")
    print(f"              PocketCoffea only checks isGlobal (mu.isGlobal == True)")
    print(f"{'='*72}")
    for ev in groups["G2"]:
        print(f"\n  run={ev[0]}  lumi={ev[1]}  event={ev[2]}")
        muons = nano_mu.get(ev, [])
        print(f"  NanoAOD muons ({len(muons)} total):")
        print_nano_muons(muons, show_id=True, show_iso=False)
        print_cmssw_mu(ev, mu_kin, g2_stages)
        for j, m in enumerate(muons):
            if m.get("isGlobal") and not m.get("isPFcand"):
                print(f"  --> Muon {j}: isGlobal=True, isPFcand=False"
                      f"  -> PC passes Stage11, CMSSW fails (needs both)")

    # -----------------------------------------------------------------------
    # G3: PC=Stage17, CMSSW=Stage14
    # -----------------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"  G3: PC=Stage17_NoDispVtx, CMSSW=Stage14_CosAlpha  ({len(groups['G3'])} events)")
    print(f"  PC passes all stages; CMSSW passes Stage14 (CosAlpha veto)")
    print(f"  but fails Stage15 (DeltaT veto)")
    print(f"{'='*72}")
    for ev in groups["G3"]:
        print(f"\n  run={ev[0]}  lumi={ev[1]}  event={ev[2]}")
        muons = nano_mu.get(ev, [])
        print(f"  NanoAOD muons ({len(muons)} total):")
        print_nano_muons(muons, show_id=True, show_iso=True)
        print_cmssw_mu(ev, mu_kin, g3_stages)


if __name__ == "__main__":
    main()
