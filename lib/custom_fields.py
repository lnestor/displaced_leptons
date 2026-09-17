import awkward as ak
import numpy as np

CENTRAL_NANOAOD_FLAG = 0

RUN_2_YEARS = ['2016_PreVFP', '2016_PostVFP', '2017', '2018']


def define_DY_flavor(events, year, is_mc, supplement_version):
    if not is_mc:
        return

    pdgid = np.abs(events.GenPart.pdgId)
    leptons = events.GenPart[
        ((pdgid == 11) | (pdgid == 13) | (pdgid == 15))
        & events.GenPart.hasFlags(["fromHardProcess", "isLastCopy"])
    ]

    n = ak.num(leptons)
    if ak.any(n != 2):
        raise ValueError(f"{ak.sum(n != 2)} events do not have exactly 2 hard-process leptons")

    different = np.abs(leptons[:, 0].pdgId) != np.abs(leptons[:, 1].pdgId)
    if ak.any(different):
        raise ValueError(f"{ak.sum(different)} events have different-flavor hard-process leptons")

    events["DYFlavor"] = np.abs(leptons[:, 0].pdgId)



def define_custom_nano_fields(events, year, is_mc, supplement_version):
    events["Electron", "original_idx"] = ak.local_index(events.Electron, axis=1)
    events["Electron", "ip3d_um"] = events.Electron.ip3d * 1e4
    events["Muon", "original_idx"] = ak.local_index(events.Muon, axis=1)
    events["Muon", "absd0_um"] = abs(events.Muon.dxybs) * 1e4

    if is_mc and "dxybs_original" in events.Muon.fields:
        events["Muon", "absd0_um_original"] = abs(events.Muon.dxybs_original) * 1e4
    else:
        events["Muon", "absd0_um_original"] = abs(events.Muon.dxybs) * 1e4

    events["Muon", "d0_um"] = events.Muon.dxybs * 1e4
    events["Muon", "ip3d_um"] = events.Muon.ip3d * 1e4

    if year in RUN_2_YEARS:
        rho = events.fixedGridRhoFastjetAll
    else:
        rho = events.Rho.fixedGridRhoFastjetAll
    events["Muon", "customIsoCorr"] = rho * np.pi * 0.4**2

    ele = events.Electron
    mu = events.Muon

    if supplement_version == CENTRAL_NANOAOD_FLAG:
        events["Electron", "customIso"] = ele.pfRelIso03_all
        events["Electron", "absd0_um"] = abs(ele.dxy) * 1e4
        events["Electron", "absd0_um_original"] = abs(events.Electron.dxy) * 1e4
        events["Electron", "sabsd0"] = abs(ele.dxy / ele.dxyErr)
        events["Electron", "d0_um"] = ele.dxy * 1e4

        eta_sc = abs(ele.deltaEtaSC + ele.eta)
        events["Electron", "is_gap"] = (eta_sc >= 1.442) & (eta_sc <= 1.566)

        events["Muon", "customIso"] = mu.pfRelIso04_all
        events["Muon", "timeAtIpInOut"] = ak.zeros_like(mu.pt)
        events["Muon", "timeNdof"] = ak.zeros_like(mu.pt)
        events["Muon", "standardIsoCorr"] = ak.zeros_like(mu.pt)

        n = len(events)
        events["InMaterialVtx"] = ak.zip({
            "lep1Idx": ak.Array([[]]*n),
            "lep2Idx": ak.Array([[]]*n),
            "lep1Flavor": ak.Array([[]]*n),
            "lep2Flavor": ak.Array([[]]*n)
        })

    if supplement_version >= 1:
        ele_iso = np.maximum(ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt + ele.pfIso03_sumNeutralEt - rho * np.pi * 0.3**2, 0) / ele.pt
        events["Electron", "customIso"] = ele_iso
        events["Electron", "absd0_um"] = abs(events.Electron.dxybs) * 1e4
        events["Electron", "sabsd0"] = abs(events.Electron.dxybs / events.Electron.dxybsErr)
        events["Electron", "d0_um"] = events.Electron.dxybs * 1e4
        events["Electron", "is_gap"] = ele.isEBEEGap

        if is_mc and "dxybs_original" in events.Electron.fields:
            events["Electron", "absd0_um_original"] = abs(events.Electron.dxybs_original) * 1e4
        else:
            events["Electron", "absd0_um_original"] = abs(events.Electron.dxybs) * 1e4

        mu_iso = np.maximum(mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutralEt - rho * np.pi * 0.4**2, 0) / mu.pt
        events["Muon", "customIso"] = mu_iso
        events["Muon", "standardIsoCorr"] = mu.pfIso04_sumPUPt / 2

    if supplement_version >= 2:
        events["Muon", "sabsd0"] = abs(events.Muon.dxybs / events.Muon.dxybsErr)
    else:
        events["Muon", "sabsd0"] = ak.full_like(events.Muon.dxybs, np.nan)


def define_gen_parent_values(events, year, is_mc, supplement_version):
    if is_mc:
        gen = events.GenPart
        idx = _get_unique_parent_idx(gen)
        safe_idx = ak.where(idx < 0, 0, idx)

        events["GenPart", "uniqueGenPartMotherPdgId"] = ak.where(idx < 0, 0, abs(gen[safe_idx].pdgId))
        events["GenPart", "uniqueGenPartMotherPt"] = ak.where(idx < 0, 0, gen[safe_idx].pt)

        matched_mu, matched_ele = _match_gen_leptons(events)

        events["Muon"] = ak.with_field(events.Muon, ak.fill_none(matched_mu.uniqueGenPartMotherPdgId, 0), "uniqueGenPartMotherPdgId")
        events["Muon"] = ak.with_field(events.Muon, ak.fill_none(matched_mu.uniqueGenPartMotherPt, 0), "uniqueGenPartMotherPt")

        events["Electron"] = ak.with_field(events.Electron, ak.fill_none(matched_ele.uniqueGenPartMotherPdgId, 0), "uniqueGenPartMotherPdgId")
        events["Electron"] = ak.with_field(events.Electron, ak.fill_none(matched_ele.uniqueGenPartMotherPt, 0), "uniqueGenPartMotherPt")


def define_gen_v0(events, year, is_mc, supplement_version):
    mu = events.Muon
    ele = events.Electron

    if is_mc:
        events["GenVtx", "v0_um"] = np.sqrt(events.GenVtx.x**2 + events.GenVtx.y**2) * 1e4

    if is_mc and supplement_version >= 2:
        events["Muon", "v0_origin_um"] = np.sqrt(mu.genVtx_x**2 + mu.genVtx_y**2) * 1e4
        events["Muon", "v0_genvtx_x_um"] = (mu.genVtx_x - events.GenVtx.x) * 1e4
        events["Muon", "v0_genvtx_y_um"] = (mu.genVtx_y - events.GenVtx.y) * 1e4
        events["Muon", "v0_genvtx_um"] = np.sqrt(
            (mu.genVtx_x - events.GenVtx.x) ** 2 + (mu.genVtx_y - events.GenVtx.y) ** 2
        ) * 1e4

        events["Electron", "v0_origin_um"] = np.sqrt(ele.genVtx_x**2 + ele.genVtx_y**2) * 1e4
        events["Electron", "v0_genvtx_x_um"] = (ele.genVtx_x - events.GenVtx.x) * 1e4
        events["Electron", "v0_genvtx_y_um"] = (ele.genVtx_y - events.GenVtx.y) * 1e4
        events["Electron", "v0_genvtx_um"] = np.sqrt(
            (ele.genVtx_x - events.GenVtx.x) ** 2 + (ele.genVtx_y - events.GenVtx.y) ** 2
        ) * 1e4

        matched_mu, matched_ele = _match_gen_leptons(events)
        mu_gen_pt = ak.fill_none(matched_mu.pt, 0)
        mu_gen_phi = ak.fill_none(matched_mu.phi, 0)
        ele_gen_pt = ak.fill_none(matched_ele.pt, 0)
        ele_gen_phi = ak.fill_none(matched_ele.phi, 0)

        mu_has_gen = mu_gen_pt > 0
        mu_gen_px = mu_gen_pt * np.cos(mu_gen_phi)
        mu_gen_py = mu_gen_pt * np.sin(mu_gen_phi)
        mu_safe_pt = ak.where(mu_has_gen, mu_gen_pt, 1)
        events["Muon", "v0_extrap_origin_um"] = ak.where(
            mu_has_gen, abs(mu.genVtx_y * mu_gen_px - mu.genVtx_x * mu_gen_py) / mu_safe_pt * 1e4, np.nan
        )
        events["Muon", "v0_extrap_genvtx_um"] = ak.where(
            mu_has_gen,
            abs((mu.genVtx_y - events.GenVtx.y) * mu_gen_px - (mu.genVtx_x - events.GenVtx.x) * mu_gen_py) / mu_safe_pt * 1e4,
            np.nan
        )

        ele_has_gen = ele_gen_pt > 0
        ele_gen_px = ele_gen_pt * np.cos(ele_gen_phi)
        ele_gen_py = ele_gen_pt * np.sin(ele_gen_phi)
        ele_safe_pt = ak.where(ele_has_gen, ele_gen_pt, 1)
        events["Electron", "v0_extrap_origin_um"] = ak.where(
            ele_has_gen, abs(ele.genVtx_y * ele_gen_px - ele.genVtx_x * ele_gen_py) / ele_safe_pt * 1e4, np.nan
        )
        events["Electron", "v0_extrap_genvtx_um"] = ak.where(
            ele_has_gen,
            abs((ele.genVtx_y - events.GenVtx.y) * ele_gen_px - (ele.genVtx_x - events.GenVtx.x) * ele_gen_py) / ele_safe_pt * 1e4,
            np.nan
        )
    else:
        events["Muon", "v0_origin_um"] = ak.full_like(mu.pt, np.nan)
        events["Muon", "v0_genvtx_x_um"] = ak.full_like(mu.pt, np.nan)
        events["Muon", "v0_genvtx_y_um"] = ak.full_like(mu.pt, np.nan)
        events["Muon", "v0_genvtx_um"] = ak.full_like(mu.pt, np.nan)
        events["Muon", "v0_extrap_origin_um"] = ak.full_like(mu.pt, np.nan)
        events["Muon", "v0_extrap_genvtx_um"] = ak.full_like(mu.pt, np.nan)

        events["Electron", "v0_origin_um"] = ak.full_like(ele.pt, np.nan)
        events["Electron", "v0_genvtx_x_um"] = ak.full_like(ele.pt, np.nan)
        events["Electron", "v0_genvtx_y_um"] = ak.full_like(ele.pt, np.nan)
        events["Electron", "v0_genvtx_um"] = ak.full_like(ele.pt, np.nan)
        events["Electron", "v0_extrap_origin_um"] = ak.full_like(ele.pt, np.nan)
        events["Electron", "v0_extrap_genvtx_um"] = ak.full_like(ele.pt, np.nan)


def define_selected_leptons(channel):
    def _fn(events, year, is_mc, supplement_version):
        (coll1, pos1), (coll2, pos2) = _get_leg_from_channel(channel)
        lep1 = events[coll1][:, pos1:pos1 + 1]
        lep2 = events[coll2][:, pos2:pos2 + 1]
        events["SelectedLeptons"] = ak.concatenate([lep1, lep2], axis=1)

    return _fn


_SYSTEMBOOST_ANCESTOR_DEPTH = 8

_SYSTEMBOOST_LEPTON_PDGID = {"ElectronGood": 11, "MuonGood": 13}


def define_systemboost(channel):
    def _fn(events, year, is_mc, supplement_version):
        n = len(events)
        (coll1, pos1), (coll2, pos2) = _get_leg_from_channel(channel)

        # reco approximation: dilepton pt + PuppiMET, built entirely from reco quantities
        # (no gen truth involved) -- this is a proxy for the system boost, not a true
        # "reco-level parent pt", see discussion. Available for both data and MC.
        reco_lep1 = ak.pad_none(events[coll1], pos1 + 1, axis=1)[:, pos1]
        reco_lep2 = ak.pad_none(events[coll2], pos2 + 1, axis=1)[:, pos2]
        lep1_pt = ak.fill_none(reco_lep1.pt, 0)
        lep1_phi = ak.fill_none(reco_lep1.phi, 0)
        lep2_pt = ak.fill_none(reco_lep2.pt, 0)
        lep2_phi = ak.fill_none(reco_lep2.phi, 0)

        px_reco = lep1_pt * np.cos(lep1_phi) + lep2_pt * np.cos(lep2_phi) + events.PuppiMET.pt * np.cos(events.PuppiMET.phi)
        py_reco = lep1_pt * np.sin(lep1_phi) + lep2_pt * np.sin(lep2_phi) + events.PuppiMET.pt * np.sin(events.PuppiMET.phi)
        pt_reco = np.sqrt(px_reco ** 2 + py_reco ** 2)

        # Nearest-common-ancestor gen matching disabled -- suspected to be causing
        # worker OOMs on high-GenPart-multiplicity samples (TTbar/DY). Not important
        # enough to keep debugging right now; pt_gen just goes to nan like the
        # not-is_mc case below.
        events["SystemBoost"] = ak.zip({"pt_gen": ak.Array(np.full(n, np.nan)), "pt_reco": pt_reco})
        return

        gen = events.GenPart
        if "original_idx" not in gen.fields:
            events["GenPart", "original_idx"] = ak.local_index(events.GenPart, axis=1)
            gen = events.GenPart

        matched1 = _match_single_lepton(events, coll1, pos1)
        matched2 = _match_single_lepton(events, coll2, pos2)

        start1 = ak.fill_none(matched1.original_idx, -1)
        start2 = ak.fill_none(matched2.original_idx, -1)

        chain1 = _ancestor_chain(gen, start1, _SYSTEMBOOST_ANCESTOR_DEPTH)
        chain2 = _ancestor_chain(gen, start2, _SYSTEMBOOST_ANCESTOR_DEPTH)

        branch1_idx, branch2_idx = _shallowest_branch_indices(chain1, chain2)
        found = (branch1_idx >= 0) & (branch2_idx >= 0)

        branch1 = _gen_lookup(gen, branch1_idx)
        branch2 = _gen_lookup(gen, branch2_idx)

        px = branch1.pt * np.cos(branch1.phi) + branch2.pt * np.cos(branch2.phi)
        py = branch1.pt * np.sin(branch1.phi) + branch2.pt * np.sin(branch2.phi)

        events["SystemBoost"] = ak.zip({
            "pt_gen": ak.where(found, np.sqrt(px ** 2 + py ** 2), 0),
            "pt_reco": pt_reco
        })

    return _fn


def _match_gen_leptons(events):
    gen = events.GenPart
    gen_mu = gen[(abs(gen.pdgId) == 13) & (gen.status == 1) & (gen.pt > 10)]
    gen_ele = gen[(abs(gen.pdgId) == 11) & (gen.status == 1) & (gen.pt > 10)]
    return _gen_match(events.Muon, gen_mu), _gen_match(events.Electron, gen_ele)


def _gen_match(coll, gen):
    dR = coll[:, :, np.newaxis].delta_r(gen[:, np.newaxis, :])
    min_dR = ak.min(dR, axis=2)
    best_idx = ak.fill_none(ak.argmin(dR, axis=2), 0)

    matched = ak.fill_none(min_dR < 0.1, False)
    gen_padded = ak.pad_none(gen, 1, axis=1)
    return ak.mask(gen_padded[best_idx], matched)


def _get_unique_parent_idx(gen):
    current_idx = gen.genPartIdxMother
    start_pdgid = abs(gen.pdgId)

    while True:
        no_mother = current_idx < 0
        safe_idx = ak.where(no_mother, 0, current_idx)
        same_pdgid = abs(gen[safe_idx].pdgId) == start_pdgid
        still_searching = ~no_mother & same_pdgid

        if not ak.any(still_searching):
            break

        next_idx = gen[safe_idx].genPartIdxMother
        current_idx = ak.where(still_searching, next_idx, current_idx)

    return current_idx


def _get_leg_from_channel(channel):
    if channel == "ee":
        return ("ElectronGood", 0), ("ElectronGood", 1)
    elif channel == "mumu":
        return ("MuonGood", 0), ("MuonGood", 1)
    elif channel == "emu":
        return ("ElectronGood", 0), ("MuonGood", 0)
    else:
        raise ValueError(f"Channel {channel} is not valid.")


def _match_single_lepton(events, coll, pos):
    gen = events.GenPart
    pdgid = _SYSTEMBOOST_LEPTON_PDGID[coll]
    gen_cands = gen[(abs(gen.pdgId) == pdgid) & (gen.status == 1) & (gen.pt > 10)]

    matched_all = _gen_match(events[coll], gen_cands)
    idx = ak.local_index(matched_all, axis=1)
    return ak.firsts(matched_all[idx == pos])


def _gen_lookup(gen, idx):
    local_idx = ak.local_index(gen, axis=1)
    safe = ak.where(idx < 0, 0, idx)
    return ak.firsts(gen[local_idx == safe[:, np.newaxis]])


def _ancestor_chain(gen, start_idx, depth):
    current = ak.fill_none(start_idx, -1)
    chain = [current]
    for _ in range(depth - 1):
        local = _gen_lookup(gen, current)
        mother = ak.fill_none(local.genPartIdxMother, -1)
        current = ak.where(current < 0, -1, mother)
        chain.append(current)
    return chain


def _shallowest_branch_indices(chain1, chain2):
    depth = len(chain1)
    branch1 = ak.full_like(chain1[0], -1)
    branch2 = ak.full_like(chain1[0], -1)
    still_searching = ak.ones_like(chain1[0], dtype=bool)

    pairs = sorted(
        ((i, j) for i in range(1, depth) for j in range(1, depth)),
        key=lambda p: (p[0] + p[1], p[0])
    )
    for i, j in pairs:
        match = still_searching & (chain1[i] >= 0) & (chain1[i] == chain2[j])
        branch1 = ak.where(match, chain1[i - 1], branch1)
        branch2 = ak.where(match, chain2[j - 1], branch2)
        still_searching = still_searching & ~match

    return branch1, branch2

