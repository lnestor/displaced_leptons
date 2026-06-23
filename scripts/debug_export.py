"""
debug_export.py

Produce a flat per-event ROOT TTree from a single NanoAOD file, with one
boolean column per cumulative cut stage, mirroring the CMSSW DebugCutflow
stages exactly.  Also writes raw kinematic variables for the leading lepton
in each collection so disagreements can be diagnosed.

Object-level cuts are broken out individually even though the main workflow
applies them all at once inside displaced_lepton_selection().

Usage:
    python debug_export.py <input.root> <output.root> <year> [nano_version]

    year:         2016_PostVFP | 2017 | 2018
    nano_version: 0 for central NanoAOD, non-zero for custom displaced-lepton
                  NanoAOD (default: auto-detect from customNanoVersion key)

Stage columns written (boolean per event):
    pass_trigger
    pass_ele_eta
    pass_ele_SC          -- cumulative: eta + SC gap veto
    pass_ele_etaphi      -- cumulative: + etaphi dead-region veto
    pass_ele_pt          -- cumulative: + pt threshold
    pass_ele_id          -- cumulative: + VID (cutBased == 4)
    pass_ele_iso         -- cumulative: + isolation  (= ElectronGood exists)
    pass_mu_eta
    pass_mu_etaphi       -- cumulative: eta + etaphi veto
    pass_mu_pt           -- cumulative: + pt threshold
    pass_mu_id           -- cumulative: + tightId
    pass_mu_iso          -- cumulative: + isolation  (= MuonGood exists)
    pass_cos_alpha       -- no back-to-back muon pair (cos alpha < -0.99)
    pass_delta_t         -- no muon pair with timing consistent with cosmics
    pass_emu_deltaR      -- any e-mu pair with deltaR > 0.2
    pass_no_disp_vtx     -- no good e-mu displaced vertex in tracker material

Kinematic columns (raw = before any selection, -999 if collection empty):
    raw_ele0_{pt,eta,phi,customIso,d0_um}
    raw_mu0_{pt,eta,phi,customIso,d0_um}
    good_ele0_{pt,eta,phi,customIso,d0_um}
    good_mu0_{pt,eta,phi,customIso,d0_um}
"""

import sys
import os
import numpy as np
import awkward as ak
import uproot
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema

# ---------------------------------------------------------------------------
# Parameters (from object_preselection.yaml and categories.yaml)
# ---------------------------------------------------------------------------

OBJ_PARAMS = {
    "Electron": {
        "2016_PostVFP": dict(pt=42, eta=1.44, iso_base=0.0588, iso_pt_dep=0,
                             id="cutBased", id_req=4),
        "2017": dict(pt=45, eta=1.44, iso_base=0.0287, iso_pt_dep=0.506,
                     id="cutBased", id_req=4,
                     etaphi_eta_min=1.0, etaphi_eta_max=1.5,
                     etaphi_phi_min=2.7, etaphi_phi_max=1e9),
        "2018": dict(pt=45, eta=1.44, iso_base=0.0287, iso_pt_dep=0.506,
                     id="cutBased", id_req=4,
                     etaphi_eta_min=0.3, etaphi_eta_max=1.2,
                     etaphi_phi_min=0.4, etaphi_phi_max=0.8),
    },
    "Muon": {
        "2016_PostVFP": dict(pt=40, eta=1.5, iso=0.1, id="tightId"),
        "2017": dict(pt=45, eta=1.5, iso=0.1, id="tightId",
                     etaphi_eta_min=1.0, etaphi_eta_max=1.5,
                     etaphi_phi_min=2.7, etaphi_phi_max=1e9),
        "2018": dict(pt=45, eta=1.5, iso=0.1, id="tightId",
                     etaphi_eta_min=0.3, etaphi_eta_max=1.2,
                     etaphi_phi_min=0.4, etaphi_phi_max=0.8),
    },
}

HLT_EMU = {
    "2016_PostVFP": ["HLT_Mu38NoFiltersNoVtx_Photon38_CaloIdL",
                     "HLT_Mu28NoFiltersNoVtxDisplaced_Photon28_CaloIdL"],
    "2017":         ["HLT_Mu43NoFiltersNoVtx_Photon43_CaloIdL"],
    "2018":         ["HLT_Mu43NoFiltersNoVtx_Photon43_CaloIdL"],
}

CENTRAL_NANO = 0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fill_none_f(arr, fill=-999.0):
    return ak.to_numpy(ak.fill_none(arr, fill)).astype(np.float32)


def fill_none_b(arr):
    return ak.to_numpy(ak.fill_none(arr, False))


def leading(coll, field, fill=-999.0):
    """Return the value of field for the leading object, -999 if empty."""
    padded = ak.pad_none(coll, 1)[:, 0]
    return fill_none_f(getattr(padded, field), fill)


def add_custom_iso(events, nano_version, year):
    """Add customIso and absd0_um fields matching workflow.py logic."""
    ele = events.Electron
    mu  = events.Muon

    if nano_version != CENTRAL_NANO:
        if year in ("2016_PreVFP", "2016_PostVFP", "2017", "2018"):
            rho = events.fixedGridRhoFastjetAll
        else:
            rho = events.Rho.fixedGridRhoFastjetAll

        ele_iso = np.maximum(
            ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt +
            ele.pfIso03_sumNeutral - rho * np.pi * 0.3**2, 0) / ele.pt
        mu_iso = np.maximum(
            mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt +
            mu.pfIso04_sumNeutral - rho * np.pi * 0.4**2, 0) / mu.pt

        events["Electron"] = ak.with_field(ele, ele_iso, "customIso")
        events["Electron"] = ak.with_field(
            events.Electron, abs(events.Electron.dxybs) * 1e4, "absd0_um")
        events["Muon"] = ak.with_field(mu, mu_iso, "customIso")
        events["Muon"] = ak.with_field(
            events.Muon, abs(events.Muon.dxybs) * 1e4, "absd0_um")
    else:
        events["Electron"] = ak.with_field(ele, ele.pfRelIso03_all, "customIso")
        events["Electron"] = ak.with_field(
            events.Electron, abs(events.Electron.dxy) * 1e4, "absd0_um")
        events["Muon"] = ak.with_field(mu, mu.pfRelIso04_all, "customIso")
        events["Muon"] = ak.with_field(
            events.Muon, abs(events.Muon.dxybs) * 1e4, "absd0_um")

    return events


def etaphi_veto_mask(coll, p):
    """True where the object is NOT in the dead pixel region."""
    if "etaphi_eta_min" not in p:
        return ak.ones_like(coll.pt, dtype=bool)
    in_region = (
        (coll.eta > p["etaphi_eta_min"]) & (coll.eta < p["etaphi_eta_max"]) &
        (coll.phi > p["etaphi_phi_min"]) & (coll.phi < p["etaphi_phi_max"])
    )
    return ~in_region


def process_chunk(events, year, nano_version):
    """Return a dict of 1-D numpy arrays, one entry per event."""
    ep = OBJ_PARAMS["Electron"][year]
    mp = OBJ_PARAMS["Muon"][year]

    # -----------------------------------------------------------------------
    # Trigger
    # -----------------------------------------------------------------------
    trig_mask = ak.zeros_like(events.event, dtype=bool)
    for path in HLT_EMU[year]:
        branch = path.replace("HLT_", "")   # coffea strips the HLT_ prefix
        if hasattr(events.HLT, branch):
            trig_mask = trig_mask | getattr(events.HLT, branch)

    # -----------------------------------------------------------------------
    # Add custom isolation and d0 fields
    # -----------------------------------------------------------------------
    events = add_custom_iso(events, nano_version, year)
    ele = events.Electron
    mu  = events.Muon

    # -----------------------------------------------------------------------
    # Per-electron sub-cut masks (all applied to the full Electron collection)
    # -----------------------------------------------------------------------
    e_eta   = abs(ele.eta) < ep["eta"]

    etaSC   = abs(ele.deltaEtaSC + ele.eta)
    e_SC    = ~((etaSC >= 1.442) & (etaSC <= 1.566))

    e_etaphi = etaphi_veto_mask(ele, ep)
    e_pt    = ele.pt > ep["pt"]
    e_id    = ele[ep["id"]] == ep["id_req"]

    iso_thresh = ep["iso_base"] + ep["iso_pt_dep"] / ele.pt
    e_iso   = ele.customIso < iso_thresh

    # Cumulative per-electron masks (each is a per-lepton boolean array)
    e_cum_eta   = e_eta
    e_cum_SC    = e_cum_eta   & e_SC
    e_cum_etaphi = e_cum_SC   & e_etaphi
    e_cum_pt    = e_cum_etaphi & e_pt
    e_cum_id    = e_cum_pt    & e_id
    e_cum_iso   = e_cum_id    & e_iso   # full object selection

    # Per-event: is there ANY electron passing the cumulative cut so far?
    pass_ele_eta    = ak.any(e_cum_eta,    axis=1)
    pass_ele_SC     = ak.any(e_cum_SC,     axis=1)
    pass_ele_etaphi = ak.any(e_cum_etaphi, axis=1)
    pass_ele_pt     = ak.any(e_cum_pt,     axis=1)
    pass_ele_id     = ak.any(e_cum_id,     axis=1)
    pass_ele_iso    = ak.any(e_cum_iso,    axis=1)  # = ElectronGood exists

    # -----------------------------------------------------------------------
    # Per-muon sub-cut masks
    # -----------------------------------------------------------------------
    m_eta    = abs(mu.eta) < mp["eta"]
    m_etaphi = etaphi_veto_mask(mu, mp)
    m_pt     = mu.pt > mp["pt"]
    # Split global (isGlobal & isPFcand) from the rest of tight ID,
    # matching CMSSW's muon_global_cut + muon_id_cut split.
    m_id     = mu.tightId
    m_iso    = mu.customIso < mp["iso"]

    m_cum_eta    = m_eta
    m_cum_etaphi = m_cum_eta    & m_etaphi
    m_cum_pt     = m_cum_etaphi & m_pt
    m_cum_id     = m_cum_pt     & m_id
    m_cum_iso    = m_cum_id     & m_iso   # full object selection

    pass_mu_eta    = ak.any(m_cum_eta,    axis=1)
    pass_mu_etaphi = ak.any(m_cum_etaphi, axis=1)
    pass_mu_pt     = ak.any(m_cum_pt,     axis=1)
    pass_mu_id     = ak.any(m_cum_id,     axis=1)
    pass_mu_iso    = ak.any(m_cum_iso,    axis=1)  # = MuonGood exists

    # -----------------------------------------------------------------------
    # Build good-lepton collections (exactly as workflow.py does)
    # -----------------------------------------------------------------------
    events["ElectronGood"] = ak.with_field(
        ele[e_cum_iso], ak.local_index(ele, axis=1)[e_cum_iso], "original_idx")
    events["MuonGood"] = ak.with_field(
        mu[m_cum_iso], ak.local_index(mu, axis=1)[m_cum_iso], "original_idx")

    nElGood = ak.num(events.ElectronGood)
    nMuGood = ak.num(events.MuonGood)

    # -----------------------------------------------------------------------
    # Category cuts (emu channel), in the same order as channel_selection.py
    # -----------------------------------------------------------------------

    # cos(alpha) veto -- mirrors get_n_back_to_back_muons(0)
    good_mu = events.MuonGood
    n_mu = ak.num(good_mu)
    has_2mu = n_mu >= 2
    mu1, mu2 = ak.unzip(ak.combinations(good_mu, 2))
    cos_alpha = (mu1.px * mu2.px + mu1.py * mu2.py + mu1.pz * mu2.pz) / (mu1.p * mu2.p)
    n_b2b = ak.sum(cos_alpha < -0.99, axis=1)
    pass_cos_alpha = n_b2b <= 0

    # Timing veto -- mirrors get_min_muon_delta_t(-20)
    # Veto events where delta_t < -20 AND both muons have ndof > 7.
    # If there are fewer than 2 muons or no pair satisfies the time cut, event passes.
    sorted_mu = good_mu[ak.argsort(good_mu.phi, axis=1, ascending=False)]
    sorted_mu = ak.pad_none(sorted_mu, 2, axis=1)
    upper = sorted_mu[:, 0]
    lower = sorted_mu[:, 1]
    delta_t = upper.timeAtIpInOut - lower.timeAtIpInOut
    both_ndof = (upper.timeNdof > 7) & (lower.timeNdof > 7)
    pass_delta_t = ~((delta_t < -20) & both_ndof)
    pass_delta_t = ak.fill_none(pass_delta_t, True)

    # e-mu deltaR > 0.2 -- mirrors get_dilepton_deltaR("emu", 0.2)
    good_ele = events.ElectronGood
    has_emu_pair = (ak.num(good_ele) >= 1) & (ak.num(good_mu) >= 1)
    e_for_dr, m_for_dr = ak.unzip(ak.cartesian([good_ele, good_mu]))
    dr = e_for_dr.delta_r(m_for_dr)
    pass_emu_deltaR = ak.any(dr > 0.2, axis=1)
    pass_emu_deltaR = ak.where(ak.is_none(pass_emu_deltaR), False, pass_emu_deltaR)

    # No good e-mu displaced vertex in tracker material
    # Mirrors get_no_in_material_vtx(MUON_FLAVOR=0, ELECTRON_FLAVOR=1)
    # MUON_FLAVOR=0 is lep1, ELECTRON_FLAVOR=1 is lep2 in the cut definition
    try:
        vtx = events.InMaterialVtx
        vtx_emu = vtx[(vtx.lep1Flavor == 0) & (vtx.lep2Flavor == 1)]
        mu0_idx  = ak.fill_none(ak.pad_none(events.MuonGood,     1)[:, 0].original_idx, -1)
        ele0_idx = ak.fill_none(ak.pad_none(events.ElectronGood, 1)[:, 0].original_idx, -1)
        match = (vtx_emu.lep1Idx == mu0_idx) & (vtx_emu.lep2Idx == ele0_idx)
        pass_no_disp_vtx = ~ak.any(match, axis=1)
    except AttributeError:
        # InMaterialVtx not present (central NanoAOD); fill True so other
        # columns are still usable
        pass_no_disp_vtx = ak.ones_like(events.event, dtype=bool)

    # -----------------------------------------------------------------------
    # Kinematics: raw leading lepton (before any selection)
    # -----------------------------------------------------------------------
    raw_ele0_pt  = leading(ele, "pt")
    raw_ele0_eta = leading(ele, "eta")
    raw_ele0_phi = leading(ele, "phi")
    raw_ele0_iso = leading(ele, "customIso")
    raw_ele0_d0  = leading(ele, "absd0_um")

    raw_mu0_pt  = leading(mu, "pt")
    raw_mu0_eta = leading(mu, "eta")
    raw_mu0_phi = leading(mu, "phi")
    raw_mu0_iso = leading(mu, "customIso")
    raw_mu0_d0  = leading(mu, "absd0_um")

    # Kinematics: leading good lepton (matching emuBranchSets in CMSSW)
    good_ele0_pt  = leading(events.ElectronGood, "pt")
    good_ele0_eta = leading(events.ElectronGood, "eta")
    good_ele0_phi = leading(events.ElectronGood, "phi")
    good_ele0_iso = leading(events.ElectronGood, "customIso")
    good_ele0_d0  = leading(events.ElectronGood, "absd0_um")

    good_mu0_pt  = leading(events.MuonGood, "pt")
    good_mu0_eta = leading(events.MuonGood, "eta")
    good_mu0_phi = leading(events.MuonGood, "phi")
    good_mu0_iso = leading(events.MuonGood, "customIso")
    good_mu0_d0  = leading(events.MuonGood, "absd0_um")

    def b(arr):
        return ak.to_numpy(arr).astype(bool)

    return {
        "run":   ak.to_numpy(events.run).astype(np.int32),
        "lumi":  ak.to_numpy(events.luminosityBlock).astype(np.int32),
        "event": ak.to_numpy(events.event).astype(np.int64),

        # cut stages
        "pass_trigger":       b(trig_mask),
        "pass_ele_eta":       b(pass_ele_eta),
        "pass_ele_SC":        b(pass_ele_SC),
        "pass_ele_etaphi":    b(pass_ele_etaphi),
        "pass_ele_pt":        b(pass_ele_pt),
        "pass_ele_id":        b(pass_ele_id),
        "pass_ele_iso":       b(pass_ele_iso),
        "pass_mu_eta":        b(pass_mu_eta),
        "pass_mu_etaphi":     b(pass_mu_etaphi),
        "pass_mu_pt":         b(pass_mu_pt),
        "pass_mu_id":         b(pass_mu_id),
        "pass_mu_iso":        b(pass_mu_iso),
        "pass_cos_alpha":     b(pass_cos_alpha),
        "pass_delta_t":       b(pass_delta_t),
        "pass_emu_deltaR":    b(pass_emu_deltaR),
        "pass_no_disp_vtx":   b(pass_no_disp_vtx),

        # raw kinematics (leading object before any selection)
        "raw_ele0_pt":   raw_ele0_pt,
        "raw_ele0_eta":  raw_ele0_eta,
        "raw_ele0_phi":  raw_ele0_phi,
        "raw_ele0_iso":  raw_ele0_iso,
        "raw_ele0_d0":   raw_ele0_d0,
        "raw_mu0_pt":    raw_mu0_pt,
        "raw_mu0_eta":   raw_mu0_eta,
        "raw_mu0_phi":   raw_mu0_phi,
        "raw_mu0_iso":   raw_mu0_iso,
        "raw_mu0_d0":    raw_mu0_d0,

        # good-lepton kinematics (after full object selection, -999 if absent)
        "good_ele0_pt":  good_ele0_pt,
        "good_ele0_eta": good_ele0_eta,
        "good_ele0_phi": good_ele0_phi,
        "good_ele0_iso": good_ele0_iso,
        "good_ele0_d0":  good_ele0_d0,
        "good_mu0_pt":   good_mu0_pt,
        "good_mu0_eta":  good_mu0_eta,
        "good_mu0_phi":  good_mu0_phi,
        "good_mu0_iso":  good_mu0_iso,
        "good_mu0_d0":   good_mu0_d0,
    }


def main():
    if len(sys.argv) < 4:
        print("Usage: python debug_export.py <input.root> <output.root> <year> [nano_version]")
        sys.exit(1)

    input_file   = sys.argv[1]
    output_file  = sys.argv[2]
    year         = sys.argv[3]
    nano_version = int(sys.argv[4]) if len(sys.argv) > 4 else None

    if year not in OBJ_PARAMS["Electron"]:
        print("Unknown year: {}".format(year))
        sys.exit(1)

    # Auto-detect nano version from the file header if not specified
    if nano_version is None:
        with uproot.open(input_file) as f:
            if "customNanoVersion" in f:
                nano_version = int(f["customNanoVersion"])
                print("Detected custom NanoAOD version {}".format(nano_version))
            else:
                nano_version = CENTRAL_NANO
                print("No customNanoVersion key found; treating as central NanoAOD")

    events = NanoEventsFactory.from_root(
        input_file,
        schemaclass=NanoAODSchema,
    ).events()

    print("Processing {} events from {}".format(len(events), input_file))

    chunk = process_chunk(events, year, nano_version)

    # Summarize pass rates for a quick sanity check
    n = len(chunk["run"])
    for col in [k for k in chunk if k.startswith("pass_")]:
        passing = int(np.sum(chunk[col]))
        print("  {:30s}: {:6d} / {:6d}".format(col, passing, n))

    with uproot.recreate(output_file) as f:
        f["debug"] = chunk

    print("Wrote {} events to {}".format(n, output_file))


if __name__ == "__main__":
    main()
