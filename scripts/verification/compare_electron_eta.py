#!/usr/bin/env python3
"""
Compare the electron eta cut between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage01JetBasicTreeMaker  -> events entering the eta cut (passed JetBasic)
  Stage02EleEtaTreeMaker    -> events passing the eta cut

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW eta, fail coffea eta: in Stage02 but not in coffea eta set
  pass coffea eta, fail CMSSW eta: in coffea eta set but not in Stage02
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

ETA_CUT   = 1.5
ETA_LABEL = f"$>=1$ e with $|\\eta| < {ETA_CUT}$"

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
se = data["stage_events"][ETA_LABEL]
c_run   = se["run"].value
c_lumi  = se["lumi"].value
c_event = se["event"].value
c_ele_pt  = se["ele_pt"].value
c_ele_eta = se["ele_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage01 = events entering the eta cut (passed JetBasic)
# Stage02 = events passing the eta cut

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "electron_etaElectron0", "electron_ptElectron0"]

s01 = f["Stage01JetBasicTreeMaker/Tree"].arrays(BRANCHES, library="np")
s02 = f["Stage02EleEtaTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s01["eventvariable_run"], s01["eventvariable_ls"], s01["eventvariable_event"])
cmssw_passed   = to_event_set(s02["eventvariable_run"], s02["eventvariable_ls"], s02["eventvariable_event"])
s01_idx = event_index(s01["eventvariable_run"], s01["eventvariable_ls"], s01["eventvariable_event"])
s02_idx = event_index(s02["eventvariable_run"], s02["eventvariable_ls"], s02["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering eta cut (Stage01): {len(cmssw_entering)}")
print(f"CMSSW passing eta cut  (Stage02): {len(cmssw_passed)}")
print(f"Coffea passing eta cut:           {len(coffea_passed)}")
print(f"Pass both:                        {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:          {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:          {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW eta, fail coffea eta (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s02_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_ele_eta={s02['electron_etaElectron0'][i]:+.3f}"
          f"  cmssw_ele_pt={s02['electron_ptElectron0'][i]:.1f}")

print()
print(f"--- Pass coffea eta, fail CMSSW eta (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s01_idx:
        j = s01_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_ele_eta={s01['electron_etaElectron0'][j]:+.3f}"
                     f"  cmssw_ele_pt={s01['electron_ptElectron0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage01 -- failed JetBasic cut)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_ele_eta={c_ele_eta[i]:+.3f}"
          f"  coffea_ele_pt={c_ele_pt[i]:.1f}"
          + cmssw_str)
