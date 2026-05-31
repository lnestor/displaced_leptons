import awkward as ak
from pocket_coffea.lib.cut_definition import Cut


def dilepton(events, params, year, sample, **kwargs):
    mask = (events.nLeptonGood >= 2)
    return ak.where(ak.is_none(mask), False, mask)

dilepton_presel = Cut(
    name="dilepton",
    params={},
    function=dilepton
)


def b2b_muons_mask(events, alpha_max=-0.99):
    mu1, mu2 = ak.unzip(ak.combinations(events.MuonGood, 2))
    cos_alpha = (mu1.px*mu2.px + mu1.py*mu2.py + mu1.pz*mu2.pz) / (mu1.p * mu2.p)
    has_back_to_back = ak.any(cos_alpha < alpha_max, axis=1)
    mask = ~has_back_to_back
    return ak.where(ak.is_none(mask), False, mask)


def _b2b_muons_impl(events, params, year, sample, **kwargs):
    return b2b_muons_mask(events, params["alpha_max"])


no_b2b_muons = Cut(
    name="no_b2b_muons",
    params={"alpha_max": -0.99},
    function=_b2b_muons_impl
)


def muon_timing_mask(events, min_delta_t = -20, min_ndof = 7):
    muons = events.MuonGood[:, :2]
    sorted_muons = muons[ak.argsort(muons.phi, axis=1, ascending=False)]

    upper = sorted_muons[:, 0]
    lower = sorted_muons[:, 0]

    delta_t = upper.timeAtIpInOut - lower.timeAtIpInOut
    both_ndof_pass = (upper.timeNdof > min_ndof) & (lower.timeNdof > min_ndof)

    return ~((delta_t < min_delta_t) & both_ndof_pass)


def in_material_vertex_mask(vertices, l1_idx, l2_idx):
    match = (vertices.lep1Idx == l1_idx) & (vertices.lep2Idx == l2_idx)
    return ~ak.any(match, axis=1)

def delta_r_mask(coll1, coll2, min_dr):
    if coll1 is coll2:
        obj1, obj2 = ak.unzip(ak.combinations(coll1, 2))
    else:
        obj1, obj2 = ak.unzip(ak.cartesian([coll1, coll2]))
    dr = obj1.delta_r(obj2)
    mask = ak.any(dr > min_dr, axis=1)
    return ak.where(ak.is_none(mask), False, mask)

def dilepton_pair(pair_str, dr_min):
    if pair_str == "ee":
        coll1, coll2 = "ElectronGood", "ElectronGood"
    elif pair_str == "mumu":
        coll1, coll2 = "MuonGood", "MuonGood"
    elif pair_str in ("emu", "mue"):
        coll1, coll2 = "ElectronGood", "MuonGood"
    else:
        raise ValueError(f"Lepton pair key {pair_str} is not valid in cut dilepton_pair")

    def _impl(events, params, year, sample, **kwargs):
        return delta_r_mask(getattr(events, params["coll1"]), getattr(events, params["coll2"]), params["dr_min"])

    return Cut(
        name=f"{pair_str}_deltaR_gt_{dr_min}",
        params={"coll1": coll1, "coll2": coll2, "dr_min": dr_min},
        function=_impl,
    )


def nObj_mask(coll, N, min_pt):
    return ak.sum(coll.pt >= min_pt, axis=1) >= N

def _get_nObj_impl(events, params, year, sample, **kwargs):
    coll = getattr(events, params["coll"])
    min_pt = params["min_pts"][year]
    return nObj_mask(coll, params["N"], min_pt)

def get_nElectrons(N, min_pts):
    return Cut(
        name=f"nElectrons_min{N}",
        params={"N": N, "coll": "ElectronGood", "min_pts": min_pts},
        function=_get_nObj_impl
    )

def get_nMuons(N, min_pts):
    return Cut(
        name=f"nMuons_min{N}",
        params={"N": N, "coll": "MuonGood", "min_pts": min_pts},
        function=_get_nObj_impl
    )

def _d0_impl(events, params, year, sample, **kwargs):
    coll1 = getattr(events, params["coll1"])
    coll2 = getattr(events, params["coll2"])
    if params["coll1"] == params["coll2"]:
        has_enough = ak.num(coll1) >= 2
        padded = ak.pad_none(coll1, 2)
        l1, l2 = padded[:, 0], padded[:, 1]
    else:
        has_enough = (ak.num(coll1) >= 1) & (ak.num(coll2) >= 1)
        l1 = ak.firsts(coll1)
        l2 = ak.firsts(coll2)

    d0_1 = ak.fill_none(l1.absd0_um, -1.0)
    d0_2 = ak.fill_none(l2.absd0_um, -1.0)

    mask = has_enough
    if params["min1"] is not None:
        mask = mask & (d0_1 > params["min1"])
    if params["max1"] is not None:
        mask = mask & (d0_1 < params["max1"])
    if params["min2"] is not None:
        mask = mask & (d0_2 > params["min2"])
    if params["max2"] is not None:
        mask = mask & (d0_2 < params["max2"])
    return mask

def d0_cuts(coll1, min1, max1, coll2, min2, max2):
    return Cut(
        name=f"d0_{coll1}{min1}{max1}_{coll2}{min2}{max2}",
        params={"coll1": coll1, "min1": min1, "max1": max1, "coll2": coll2, "min2": min2, "max2": max2},
        function=_d0_impl
    )
