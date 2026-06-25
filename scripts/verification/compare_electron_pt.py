#!/usr/bin/env python3
"""
Compare the electron pt cut between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage04EleEtaPhiVetoTreeMaker -> events entering the pt cut (passed etaphi veto)
  Stage05ElePtTreeMaker         -> events passing the pt cut

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW pt, fail coffea pt: in Stage05 but not in coffea pt set
  pass coffea pt, fail CMSSW pt: in coffea pt set but not in Stage05
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

PT_LABEL = "$>=1$ e with $p_T > 45$ GeV"

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
se = data["stage_events"][PT_LABEL]
c_run   = se["run"].value
c_lumi  = se["lumi"].value
c_event = se["event"].value
c_ele_pt  = se["ele_pt"].value
c_ele_eta = se["ele_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage04 = events entering the pt cut (passed etaphi veto)
# Stage05 = events passing the pt cut

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "electron_etaElectron0", "electron_ptElectron0"]

s04 = f["Stage04EleEtaPhiVetoTreeMaker/Tree"].arrays(BRANCHES, library="np")
s05 = f["Stage05ElePtTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s04["eventvariable_run"], s04["eventvariable_ls"], s04["eventvariable_event"])
cmssw_passed   = to_event_set(s05["eventvariable_run"], s05["eventvariable_ls"], s05["eventvariable_event"])
s04_idx = event_index(s04["eventvariable_run"], s04["eventvariable_ls"], s04["eventvariable_event"])
s05_idx = event_index(s05["eventvariable_run"], s05["eventvariable_ls"], s05["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering pt cut (Stage04): {len(cmssw_entering)}")
print(f"CMSSW passing pt cut  (Stage05): {len(cmssw_passed)}")
print(f"Coffea passing pt cut:           {len(coffea_passed)}")
print(f"Pass both:                       {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:         {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:         {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW pt, fail coffea pt (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s05_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_ele_eta={s05['electron_etaElectron0'][i]:+.3f}"
          f"  cmssw_ele_pt={s05['electron_ptElectron0'][i]:.1f}")

print()
print(f"--- Pass coffea pt, fail CMSSW pt (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s04_idx:
        j = s04_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_ele_eta={s04['electron_etaElectron0'][j]:+.3f}"
                     f"  cmssw_ele_pt={s04['electron_ptElectron0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage04 -- failed etaphi veto)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_ele_eta={c_ele_eta[i]:+.3f}"
          f"  coffea_ele_pt={c_ele_pt[i]:.1f}"
          + cmssw_str)
