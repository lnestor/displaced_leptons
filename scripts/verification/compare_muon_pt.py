#!/usr/bin/env python3
"""
Compare the muon pt cut between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage09MuEtaPhiVetoTreeMaker -> events entering the muon pt cut (passed etaphi)
  Stage10MuPtTreeMaker         -> events passing the muon pt cut

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW mu pt, fail coffea mu pt: in Stage10 but not in coffea mu pt set
  pass coffea mu pt, fail CMSSW mu pt: in coffea mu pt set but not in Stage10
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

PT_LABEL = "$>=1$ $\\mu$ with $p_T > 45$ GeV"

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
c_mu_pt  = se["mu_pt"].value
c_mu_eta = se["mu_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage09 = events entering the muon pt cut (passed etaphi veto)
# Stage10 = events passing the muon pt cut

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "muon_etaMuon0", "muon_ptMuon0"]

s09 = f["Stage09MuEtaPhiVetoTreeMaker/Tree"].arrays(BRANCHES, library="np")
s10 = f["Stage10MuPtTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s09["eventvariable_run"], s09["eventvariable_ls"], s09["eventvariable_event"])
cmssw_passed   = to_event_set(s10["eventvariable_run"], s10["eventvariable_ls"], s10["eventvariable_event"])
s09_idx = event_index(s09["eventvariable_run"], s09["eventvariable_ls"], s09["eventvariable_event"])
s10_idx = event_index(s10["eventvariable_run"], s10["eventvariable_ls"], s10["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering mu pt cut (Stage09): {len(cmssw_entering)}")
print(f"CMSSW passing mu pt cut  (Stage10): {len(cmssw_passed)}")
print(f"Coffea passing mu pt cut:           {len(coffea_passed)}")
print(f"Pass both:                          {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:            {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:            {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW mu pt, fail coffea mu pt (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s10_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_mu_eta={s10['muon_etaMuon0'][i]:+.3f}"
          f"  cmssw_mu_pt={s10['muon_ptMuon0'][i]:.1f}")

print()
print(f"--- Pass coffea mu pt, fail CMSSW mu pt (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s09_idx:
        j = s09_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_mu_eta={s09['muon_etaMuon0'][j]:+.3f}"
                     f"  cmssw_mu_pt={s09['muon_ptMuon0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage09 -- failed etaphi veto)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_mu_eta={c_mu_eta[i]:+.3f}"
          f"  coffea_mu_pt={c_mu_pt[i]:.1f}"
          + cmssw_str)
