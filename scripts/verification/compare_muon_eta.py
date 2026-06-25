#!/usr/bin/env python3
"""
Compare the muon eta cut between coffea and CMSSW DisplacedSUSY.

CMSSW stage semantics: StageN tree = events PASSING cut N.
  Stage07EleIsoTreeMaker -> events entering the muon eta cut (passed ele iso)
  Stage08MuEtaTreeMaker  -> events passing the muon eta cut

Coffea semantics: stage_events[label] = events passing that cut (cumulative).

Disagreements (after removing known reasons):
  pass CMSSW mu eta, fail coffea mu eta: in Stage08 but not in coffea mu eta set
  pass coffea mu eta, fail CMSSW mu eta: in coffea mu eta set but not in Stage08
"""

import csv
import os
import uproot
import coffea.util
import numpy as np

COFFEA_FILE   = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/output/cmssw_compare_v2/v1/output_all.coffea"
ROOT_FILE     = "/uscms/homes/l/lnestor/nobackup/displaced_leptons/hist_Stage00Trigger_2026_06_06_15h14m36s.root"
KNOWN_REASONS = os.path.join(os.path.dirname(__file__), "known_reasons.csv")

ETA_LABEL = "$>=1$ $\\mu$ with $|\\eta| < 1.5$"

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
c_mu_pt  = se["mu_pt"].value
c_mu_eta = se["mu_eta"].value

coffea_passed = to_event_set(c_run, c_lumi, c_event)
coffea_idx    = event_index(c_run, c_lumi, c_event)

# -- Load CMSSW trees ----------------------------------------------------------
# Stage07 = events entering the muon eta cut (passed ele iso)
# Stage08 = events passing the muon eta cut

f = uproot.open(ROOT_FILE)

BRANCHES = ["eventvariable_run", "eventvariable_ls", "eventvariable_event",
            "muon_etaMuon0", "muon_ptMuon0"]

s07 = f["Stage07EleIsoTreeMaker/Tree"].arrays(BRANCHES, library="np")
s08 = f["Stage08MuEtaTreeMaker/Tree"].arrays(BRANCHES, library="np")

cmssw_entering = to_event_set(s07["eventvariable_run"], s07["eventvariable_ls"], s07["eventvariable_event"])
cmssw_passed   = to_event_set(s08["eventvariable_run"], s08["eventvariable_ls"], s08["eventvariable_event"])
s07_idx = event_index(s07["eventvariable_run"], s07["eventvariable_ls"], s07["eventvariable_event"])
s08_idx = event_index(s08["eventvariable_run"], s08["eventvariable_ls"], s08["eventvariable_event"])

# -- Compare -------------------------------------------------------------------

pass_cmssw_fail_coffea = sorted(cmssw_passed - coffea_passed - known_events)
pass_coffea_fail_cmssw = sorted(coffea_passed - cmssw_passed - known_events)
pass_both = cmssw_passed & coffea_passed

print(f"CMSSW entering mu eta cut (Stage07): {len(cmssw_entering)}")
print(f"CMSSW passing mu eta cut  (Stage08): {len(cmssw_passed)}")
print(f"Coffea passing mu eta cut:           {len(coffea_passed)}")
print(f"Pass both:                           {len(pass_both)}")
print(f"Pass CMSSW, fail coffea:             {len(pass_cmssw_fail_coffea)}")
print(f"Pass coffea, fail CMSSW:             {len(pass_coffea_fail_cmssw)}")
print()

# -- Print kinematics for disagreeing events -----------------------------------

print(f"--- Pass CMSSW mu eta, fail coffea mu eta (showing {min(N_PRINT, len(pass_cmssw_fail_coffea))}) ---")
for run, lumi, event in pass_cmssw_fail_coffea[:N_PRINT]:
    i = s08_idx[(run, lumi, event)]
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  cmssw_mu_eta={s08['muon_etaMuon0'][i]:+.3f}"
          f"  cmssw_mu_pt={s08['muon_ptMuon0'][i]:.1f}")

print()
print(f"--- Pass coffea mu eta, fail CMSSW mu eta (showing {min(N_PRINT, len(pass_coffea_fail_cmssw))}) ---")
for run, lumi, event in pass_coffea_fail_cmssw[:N_PRINT]:
    i = coffea_idx[(run, lumi, event)]
    cmssw_str = ""
    if (run, lumi, event) in s07_idx:
        j = s07_idx[(run, lumi, event)]
        cmssw_str = (f"  cmssw_mu_eta={s07['muon_etaMuon0'][j]:+.3f}"
                     f"  cmssw_mu_pt={s07['muon_ptMuon0'][j]:.1f}")
    else:
        cmssw_str = "  (not in CMSSW Stage07 -- failed ele iso cut)"
    print(f"  run={run:>7}  lumi={lumi:>5}  event={event:>12}"
          f"  coffea_mu_eta={c_mu_eta[i]:+.3f}"
          f"  coffea_mu_pt={c_mu_pt[i]:.1f}"
          + cmssw_str)
