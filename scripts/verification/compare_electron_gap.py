#!/usr/bin/env python3
"""
Compare the electron supercluster gap veto between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage02EleEtaTreeMaker    -> events entering the gap veto (passed eta)
  Stage03EleGapVetoTreeMaker -> events passing the gap veto

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW gap, fail coffea gap: in Stage03 but not in coffea gap set
  pass coffea gap, fail CMSSW gap: in coffea gap set but not in Stage03
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

GAP_LABEL = "$>=1$ e not in supercluster gap"

N_PRINT = 10


def to_event_set(run, lumi, event):
    return set(zip(run.astype(np.int64), lumi.astype(np.int64), event.astype(np.int64)))


def event_index(run, lumi, event):
    return {(int(r), int(l), int(e)): i
            for i, (r, l, e) in enumerate(zip(run, lumi, event))}


# -- Load known reasons --------------------------------------------------------

known_events = set()
if os.path.exists(KNOWN_REASONS):
    with open(KNOWN_REASONS, newline="") as f:
        for row in csv.DictReader(f):
            known_events.add((int(row["run"]), int(row["lumi"]), int(row["event"])))
    print(f"Loaded {len(known_events)} known events from {KNOWN_REASONS}")

# -- Load coffea ---------------------------------------------------------------

data = coffea.util.load(COFFEA_FILE)
se = data["stage_events"][GAP_LABEL]
c_run   = se["run"].value
c_lumi  = se["lumi"].value
c_event = se["event"].value
c_ele_pt  = se["ele_pt"].value
c_ele_eta = se["ele_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage02 = events entering the gap cut (passing eta)
# Stage03 = events passing the gap veto

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "electron_etaElectron0", "electron_ptElectron0"]

s02 = f["Stage02EleEtaTreeMaker/Tree"].arrays(BRANCHES, library="np")
s03 = f["Stage03EleGapVetoTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s02["eventvariable_run"], s02["eventvariable_ls"], s02["eventvariable_event"])
cmssw_passed   = to_event_set(s03["eventvariable_run"], s03["eventvariable_ls"], s03["eventvariable_event"])
s02_idx = event_index(s02["eventvariable_run"], s02["eventvariable_ls"], s02["eventvariable_event"])
s03_idx = event_index(s03["eventvariable_run"], s03["eventvariable_ls"], s03["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering gap veto (Stage02): {len(cmssw_entering)}")
print(f"CMSSW passing gap veto  (Stage03): {len(cmssw_passed)}")
print(f"Coffea passing gap veto:           {len(coffea_passed)}")
print(f"Pass both:                         {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:           {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:           {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW gap, fail coffea gap (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s03_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_ele_eta={s03['electron_etaElectron0'][i]:+.3f}"
          f"  cmssw_ele_pt={s03['electron_ptElectron0'][i]:.1f}")

print()
print(f"--- Pass coffea gap, fail CMSSW gap (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s02_idx:
        j = s02_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_ele_eta={s02['electron_etaElectron0'][j]:+.3f}"
                     f"  cmssw_ele_pt={s02['electron_ptElectron0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage02 -- failed eta cut)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_ele_eta={c_ele_eta[i]:+.3f}"
          f"  coffea_ele_pt={c_ele_pt[i]:.1f}"
          + cmssw_str)
