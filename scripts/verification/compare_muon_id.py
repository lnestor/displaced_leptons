#!/usr/bin/env python3
"""
Compare the muon tight ID cut between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage11MuGlobalTreeMaker -> events entering the muon ID cut (passed global req.)
  Stage12MuIDTreeMaker     -> events passing the muon tight ID cut

Note: CMSSW has a separate Stage11MuGlobal cut that coffea does not. The coffea
tight muon ID subsumes the global requirement, so Stage12 is the correct
CMSSW counterpart to coffea's muon ID stage.

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW mu ID, fail coffea mu ID: in Stage12 but not in coffea mu ID set
  pass coffea mu ID, fail CMSSW mu ID: in coffea mu ID set but not in Stage12
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

ID_LABEL = "$>=1$ $\\mu$ passing tight ID"

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
se = data["stage_events"][ID_LABEL]
c_run   = se["run"].value
c_lumi  = se["lumi"].value
c_event = se["event"].value
c_mu_pt  = se["mu_pt"].value
c_mu_eta = se["mu_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage11 = events entering the muon ID cut (passed global requirement)
# Stage12 = events passing the muon tight ID cut

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "muon_etaMuon0", "muon_ptMuon0"]

s11 = f["Stage11MuGlobalTreeMaker/Tree"].arrays(BRANCHES, library="np")
s12 = f["Stage12MuIDTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s11["eventvariable_run"], s11["eventvariable_ls"], s11["eventvariable_event"])
cmssw_passed   = to_event_set(s12["eventvariable_run"], s12["eventvariable_ls"], s12["eventvariable_event"])
s11_idx = event_index(s11["eventvariable_run"], s11["eventvariable_ls"], s11["eventvariable_event"])
s12_idx = event_index(s12["eventvariable_run"], s12["eventvariable_ls"], s12["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering mu ID cut (Stage11): {len(cmssw_entering)}")
print(f"CMSSW passing mu ID cut  (Stage12): {len(cmssw_passed)}")
print(f"Coffea passing mu ID cut:           {len(coffea_passed)}")
print(f"Pass both:                          {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:            {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:            {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW mu ID, fail coffea mu ID (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s12_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_mu_eta={s12['muon_etaMuon0'][i]:+.3f}"
          f"  cmssw_mu_pt={s12['muon_ptMuon0'][i]:.1f}")

print()
print(f"--- Pass coffea mu ID, fail CMSSW mu ID (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s11_idx:
        j = s11_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_mu_eta={s11['muon_etaMuon0'][j]:+.3f}"
                     f"  cmssw_mu_pt={s11['muon_ptMuon0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage11 -- failed global cut)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_mu_eta={c_mu_eta[i]:+.3f}"
          f"  coffea_mu_pt={c_mu_pt[i]:.1f}"
          + cmssw_str)
