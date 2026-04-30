import awkward as ak
from pocket_coffea.lib.cut_definition import Cut

def dilepton(events, params, year, sample, **kwargs):
    mask = (events.nLeptonGood >= 2)

    return ak.where(ak.is_none(mask), False, mask)

dilepton_presel = Cut(
    name="dilepton",
    params={ },
    function=dilepton
)

def b2b_muons(events, params, year, sample, **kwargs):
    mu1, mu2 = ak.unzip(ak.combinations(events.MuonGood, 2))
    cos_alpha = (mu1.px*mu2.px + mu1.py*mu2.py + mu1.pz*mu2.pz) / (mu1.p * mu2.p)
    has_back_to_back = ak.any(cos_alpha < params["alpha_max"], axis=1)
    mask = ~has_back_to_back
    return ak.where(ak.is_none(mask), False, mask)

no_b2b_muons = Cut(
    name="Has back to back muons",
    params={"alpha_max": -0.99},
    function=b2b_muons
)

def _deltaR_impl(events, params, year, sample, **kwargs):
    col1 = getattr(events, params["col1"])
    col2 = getattr(events, params["col2"])
    if params["col1"] == params["col2"]:
      l1, l2 = ak.unzip(ak.combinations(col1, 2))
    else:
      l1, l2 = ak.unzip(ak.cartesian([col1, col2]))
    dr = l1.delta_r(l2)
    mask = ak.any(dr > params["dr_min"], axis=1)
    return ak.where(ak.is_none(mask), False, mask)

def dilepton_pair(pair_str, dr_min):
    if pair_str == "ee":
        col1 = "ElectronGood"
        col2 = "ElectronGood"
    elif pair_str == "mumu":
        col1 = "MuonGood"
        col2 = "MuonGood"
    elif pair_str == "emu" or pair_str == "mue":
        col1 = "ElectronGood"
        col2 = "MuonGood"
    else:
        raise ValueError(f"Lepton pair key {pair_str} is not valid in cut dilepton_pair")

    return Cut(
      name=f"{pair_str}_deltaR_gt_{dr_min}",
      params={"col1": col1, "col2": col2, "dr_min": dr_min},
      function=_deltaR_impl,
    )

def _get_nObj_impl(events, params, year, sample, **kwargs):
    return ak.sum(events[params["coll"]].pt >= params["min_pts"][year], axis=1) >= params["N"]

def get_nElectrons(N, min_pts):
    name = f"nElectrons_min{N}"
    return Cut(
        name=name,
        params={"N": N, "coll": "ElectronGood", "min_pts": min_pts},
        function=_get_nObj_impl
    )

def get_nMuons(N, min_pts):
    name = f"nMuons_min{N}"
    return Cut(
        name=name,
        params={"N": N, "coll": "MuonGood", "min_pts": min_pts},
        function=_get_nObj_impl
    )
