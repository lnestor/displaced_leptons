#!/usr/bin/env python3
"""
Append known gap-definition disagreement events to known_reasons.csv.

These 20 events pass CMSSW's EleGapVeto (which uses isEBEEGap) but fail
coffea's gap veto (which uses abs(deltaEtaSC + eta) in [1.442, 1.566] for
custom NanoAOD). The two definitions disagree for electrons near the gap
boundary. They will be reconciled once isEBEEGap is stored in the custom
NanoAOD.
"""

import csv
import os

OUT_CSV = os.path.join(os.path.dirname(__file__), "known_reasons.csv")
REASON  = "gap_definition_diff"

EVENTS = [
    (319656, 102,  65943302),
    (319656, 106,  71907661),
    (319656, 133, 110009458),
    (319656, 140, 121444001),
    (319656, 141, 123130527),
    (319656, 148, 136445000),
    (319657, 130, 212398903),
    (319678,  57,  43219142),
    (319678,  57,  44553443),
    (319678,  65,  57156311),
    (319678,  65,  58100643),
    (319678,  70,  66111872),
    (319678,  76,  76448489),
    (319678,  85,  89987413),
    (319678,  86,  92630660),
    (319678,  86,  92775470),
    (319678,  87,  94088461),
    (319678,  98, 110192732),
    (319678, 106, 122904190),
    (319678, 106, 124240653),
]

# Events where the electron surviving the etaphi veto has pt < 5 GeV (NanoAOD
# floor), but the pt_floor scan missed them because a higher-pt electron exists
# in the MiniAOD that is later cut by the etaphi veto.
ETAPHI_PT_FLOOR_EVENTS = [
    (319678, 87, 94003006),
]
ETAPHI_PT_FLOOR_REASON = "nano_ele_pt_floor_after_etaphi"

with open(OUT_CSV, "a", newline="") as f:
    writer = csv.writer(f)
    for run, lumi, event in EVENTS:
        writer.writerow([run, lumi, event, REASON])
    for run, lumi, event in ETAPHI_PT_FLOOR_EVENTS:
        writer.writerow([run, lumi, event, ETAPHI_PT_FLOOR_REASON])

print(f"Appended {len(EVENTS)} gap_definition_diff events to {OUT_CSV}")
print(f"Appended {len(ETAPHI_PT_FLOOR_EVENTS)} nano_ele_pt_floor_after_etaphi events to {OUT_CSV}")
