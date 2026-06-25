#!/usr/bin/env python3
"""
Find events where every electron passing |eta| < ETA_CUT is below the NanoAOD
pt floor (pt < PT_FLOOR), and write them to known_reasons.csv.

NanoAOD drops all electrons with pt < 5 GeV, so coffea cannot see them. If an
event has no electrons above the floor that also pass the eta cut, coffea will
fail the eta stage for a different reason than the CMSSW analysis.

Reads from the MiniAOD-level ntuple so the check is independent of any CMSSW
stage.
"""

import csv
import os
import uproot
import awkward as ak
import numpy as np

NTUPLE_FILE = os.path.join(
    os.path.dirname(__file__),
    "../old_verification/MuonEG_2018C_12E70CDF-E883-344D-94E8-718CAF99128E/miniaod_ntuple.root",
)
OUT_CSV  = os.path.join(os.path.dirname(__file__), "known_reasons.csv")
REASON   = "nano_ele_pt_floor"
ETA_CUT  = 1.5
PT_FLOOR = 5.0

f = uproot.open(NTUPLE_FILE)
t = f["Events"]

runs   = t["run"].array(library="np")
lumis  = t["lumi"].array(library="np")
events = t["event"].array(library="np")
ele_pt  = t["Electron_pt"].array(library="ak")
ele_eta = t["Electron_eta"].array(library="ak")

# electrons that pass the eta cut
in_eta = abs(ele_eta) < ETA_CUT
pt_in_eta = ele_pt[in_eta]

# events where at least one electron passes eta but ALL of them are below the floor
has_eta_ele     = ak.num(pt_in_eta) > 0
all_below_floor = ak.all(pt_in_eta < PT_FLOOR, axis=1)
flag = has_eta_ele & all_below_floor

rows = list(zip(
    runs[ak.to_numpy(flag)].astype(int),
    lumis[ak.to_numpy(flag)].astype(int),
    events[ak.to_numpy(flag)].astype(int),
))

print(f"Events with all eta-passing electrons below NanoAOD pt floor ({PT_FLOOR} GeV): {len(rows)}")

with open(OUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["run", "lumi", "event", "reason"])
    for run, lumi, event in rows:
        writer.writerow([run, lumi, event, REASON])

print(f"Wrote {len(rows)} rows to {OUT_CSV}")
