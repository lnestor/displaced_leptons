#!/usr/bin/env python3
"""
Inspect two events from MiniAOD to understand why their muons are absent
from NanoAOD despite having pt > 3 GeV.

NanoAOD finalMuons filter (CMSSW_10_2_22 muons_cff.py):
    pt > 3 && (passed('CutBasedIdLoose') || passed('SoftCutBasedId') ||
               passed('SoftMvaId') || passed('CutBasedIdGlobalHighPt') ||
               passed('CutBasedIdTrkHighPt'))

Events under investigation:
  run=319678, lumi=57,  event=44158444   -- CMSSW muon pt=14.5, NanoAOD has 0 muons
  run=319678, lumi=229, event=328368034  -- CMSSW muon pt=3.7,  NanoAOD has different muon

Usage: python inspect_miniaod_muons.py
       (must be run inside cmsenv)
"""

import ROOT
ROOT.gSystem.Load("libFWCoreFWLite")
ROOT.FWLiteEnabler.enable()
from DataFormats.FWLite import Events, Handle

MINIAOD = "MuonEG_2018C.root"

TARGETS = {
    (319678, 57,  44158444),
    (319678, 229, 328368034),
}

# reco::Muon::Selector bits from DataFormats/MuonReco/interface/Muon.h @ CMSSW_10_2_22.
# NOTE: these differ significantly from CMSSW 13+ where the iso bits were removed
# and the ID bits were renumbered. Always use the tag-matched enum when reading
# a MiniAOD produced with a specific CMSSW version.
SELECTORS = [
    ("CutBasedIdLoose",        1 << 0,  True),
    ("CutBasedIdMedium",       1 << 1,  False),
    ("CutBasedIdMediumPrompt", 1 << 2,  False),
    ("CutBasedIdTight",        1 << 3,  False),
    ("CutBasedIdGlobalHighPt", 1 << 4,  True),
    ("CutBasedIdTrkHighPt",    1 << 5,  True),
    ("PFIsoVeryLoose",         1 << 6,  False),
    ("PFIsoLoose",             1 << 7,  False),
    ("PFIsoMedium",            1 << 8,  False),
    ("PFIsoTight",             1 << 9,  False),
    ("PFIsoVeryTight",         1 << 10, False),
    ("TkIsoLoose",             1 << 11, False),
    ("TkIsoTight",             1 << 12, False),
    ("SoftCutBasedId",         1 << 13, True),
    ("SoftMvaId",              1 << 14, True),
    ("MvaLoose",               1 << 15, False),
    ("MvaMedium",              1 << 16, False),
    ("MvaTight",               1 << 17, False),
    ("MiniIsoLoose",           1 << 18, False),
    ("MiniIsoMedium",          1 << 19, False),
    ("MiniIsoTight",           1 << 20, False),
    ("MiniIsoVeryTight",       1 << 21, False),
    ("TriggerIdLoose",         1 << 22, False),
    ("InTimeMuon",             1 << 23, False),
]
# Third element: True = used in NanoAOD finalMuons filter


def print_muon(i, mu):
    sel = mu.selectors()
    nano_ids = [name for name, bit, in_nano in SELECTORS if in_nano and (sel & bit)]
    passes_nano = mu.pt() > 3.0 and len(nano_ids) > 0

    print(f"\n  Muon {i}:  pt={mu.pt():.3f}  eta={mu.eta():.4f}  phi={mu.phi():.4f}"
          f"  charge={mu.charge()}")
    print(f"    isGlobal={mu.isGlobalMuon()}  isPF={mu.isPFMuon()}"
          f"  isTracker={mu.isTrackerMuon()}  isStandAlone={mu.isStandAloneMuon()}")
    print(f"    selectors = 0x{sel:08x}")
    for name, bit, in_nano in SELECTORS:
        tag = "  <-- NanoAOD filter" if in_nano else ""
        print(f"      {name:<28} = {bool(sel & bit)}{tag}")
    print(f"    --> passes NanoAOD filter (pt>3 + ID): {passes_nano}"
          f"  (passing IDs: {nano_ids if nano_ids else 'none'})")


handle = Handle("std::vector<pat::Muon>")

events = Events(MINIAOD)
found = 0
for event in events:
    aux = event.eventAuxiliary()
    eid = (int(aux.run()), int(aux.luminosityBlock()), int(aux.event()))
    if eid not in TARGETS:
        continue
    found += 1
    print(f"\n{'='*72}")
    print(f"  run={eid[0]}  lumi={eid[1]}  event={eid[2]}")
    print(f"{'='*72}")
    event.getByLabel("slimmedMuons", handle)
    muons = handle.product()
    print(f"  {len(muons)} muons in slimmedMuons collection:")
    for i, mu in enumerate(muons):
        print_muon(i, mu)
    if found == len(TARGETS):
        break

print(f"\nDone. Found {found}/{len(TARGETS)} target events.")
