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

        mu_iso = np.maximum(mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutralEt - rho * np.pi * 0.4**2, 0) / mu.pt
        events["Muon", "customIso"] = mu_iso
        events["Muon", "standardIsoCorr"] = mu.pfIso04_sumPUPt / 2

    if supplement_version >= 2:
        events["Muon", "sabsd0"] = abs(events.Muon.dxybs / events.Muon.dxybsErr)
        if is_mc:
            events["Muon", "gen_absd0_um"] = np.sqrt(mu.genVtx_x**2 + mu.genVtx_y**2) * 1e4
            events["Electron", "gen_absd0_um"] = np.sqrt(ele.genVtx_x**2 + ele.genVtx_y**2) * 1e4
        else:
            events["Muon", "gen_absd0_um"] = ak.full_like(mu.pt, np.nan)
            events["Electron", "gen_absd0_um"] = ak.full_like(ele.pt, np.nan)
    else:
        events["Muon", "gen_absd0_um"] = ak.full_like(mu.pt, np.nan)
        events["Electron", "gen_absd0_um"] = ak.full_like(ele.pt, np.nan)
        events["Muon", "sabsd0"] = ak.full_like(events.Muon.dxybs, np.nan)


def define_gen_parent(events, year, is_mc, supplement_version):
    if is_mc:
        gen = events.GenPart
        events["GenPart"] = ak.with_field(events.GenPart, _get_unique_parent_pdgid(gen), "uniqueGenPartMotherIdx")
        gen = events.GenPart
        ele = events.Electron
        mu = events.Muon

        gen_mu = gen[(abs(gen.pdgId) == 13) & (gen.status == 1) & (gen.pt > 10)]
        matched_mu = _gen_match(mu, gen_mu)
        events["Muon"] = ak.with_field(events.Muon, ak.fill_none(matched_mu.uniqueGenPartMotherIdx, 0), "uniqueGenPartMotherIdx")

        gen_ele = gen[(abs(gen.pdgId) == 11) & (gen.status == 1) & (gen.pt > 10)]
        matched_ele = _gen_match(ele, gen_ele)
        events["Electron"] = ak.with_field(events.Electron, ak.fill_none(matched_ele.uniqueGenPartMotherIdx, 0), "uniqueGenPartMotherIdx")


def _gen_match(coll, gen):
    dR = coll[:, :, np.newaxis].delta_r(gen[:, np.newaxis, :])
    min_dR = ak.min(dR, axis=2)
    best_idx = ak.fill_none(ak.argmin(dR, axis=2), 0)

    matched = ak.fill_none(min_dR < 0.1, False)
    gen_padded = ak.pad_none(gen, 1, axis=1)
    return ak.mask(gen_padded[best_idx], matched)


def _get_unique_parent_pdgid(gen):
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

    safe_idx = ak.where(current_idx < 0, 0, current_idx)
    return ak.where(current_idx < 0, 0, abs(gen[safe_idx].pdgId))

