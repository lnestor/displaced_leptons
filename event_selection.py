import awkward as ak
from pocket_coffea.lib.cut_definition import Cut


MUON_FLAVOR = 0
ELECTRON_FLAVOR = 1

_FLAVOR_NAME = {MUON_FLAVOR: "mu", ELECTRON_FLAVOR: "e"}


def get_nLeptonGood(N):
    def _impl(events, params, **kwargs):
        mask = events.nLeptonGood >= params["N"]
        return ak.where(ak.is_none(mask), False, mask)
    return Cut(name=f"nLeptonGood_{N}", params={"N": N}, function=_impl)


def get_n_back_to_back_muons(max_pairs, coll):
    def _impl(events, params, **kwargs):
        mu1, mu2 = ak.unzip(ak.combinations(getattr(events, params["coll"]), 2))
        cos_alpha = (mu1.px*mu2.px + mu1.py*mu2.py + mu1.pz*mu2.pz) / (mu1.p * mu2.p)

        n_b2b = ak.sum(cos_alpha < -0.99, axis=1)
        mask = n_b2b <= params["max_pairs"]
        return ak.where(ak.is_none(mask), False, mask)
    return Cut(name=f"n_back_to_back_muons_max{max_pairs}", params={"max_pairs": max_pairs, "coll": coll}, function=_impl)


def get_min_muon_delta_t(min_delta_t, coll):
    def _impl(events, params, **kwargs):
        muons = getattr(events, params["coll"])[:, :2]
        sorted_muons = muons[ak.argsort(muons.phi, axis=1, ascending=False)]
        sorted_muons = ak.pad_none(sorted_muons, 2, axis=1)

        upper = sorted_muons[:, 0]
        lower = sorted_muons[:, 1]

        delta_t = upper.timeAtIpInOut - lower.timeAtIpInOut
        both_ndof_pass = (upper.timeNdof > 7) & (lower.timeNdof > 7)

        mask = ~((delta_t < params["min_delta_t"]) & both_ndof_pass)
        return ak.fill_none(mask, True)

    return Cut(name=f"min_muon_delta_t_{min_delta_t}", params={"min_delta_t": min_delta_t, "coll": coll}, function=_impl)


def get_no_in_material_vtx(flavor1, flavor2, coll1, coll2):
    def _impl(events, params, **kwargs):
        vtx = events.InMaterialVtx[
            (events.InMaterialVtx.lep1Flavor == params["flavor1"]) *
            (events.InMaterialVtx.lep2Flavor == params["flavor2"])
        ]

        if params["coll1"] == params["coll2"]:
            coll = ak.pad_none(getattr(events, params["coll1"]), 2)
            l1_idx, l2_idx = coll[:, 0].original_idx, coll[:, 1].original_idx
        else:
            l1_idx = ak.pad_none(getattr(events, params["coll1"]), 1)[:, 0].original_idx
            l2_idx = ak.pad_none(getattr(events, params["coll2"]), 1)[:, 0].original_idx

        match = (vtx.lep1Idx == l1_idx) & (vtx.lep2Idx == l2_idx)
        return ~ak.any(match, axis=1)

    return Cut(
        name=f"no_in_material_vtx_{_FLAVOR_NAME[flavor1]}{_FLAVOR_NAME[flavor2]}",
        params={"flavor1": flavor1, "flavor2": flavor2, "coll1": coll1, "coll2": coll2},
        function=_impl
    )


def get_dilepton_deltaR(pair_str, dr_min, coll1, coll2):
    def _impl(events, params, **kwargs):
        c1 = getattr(events, params["coll1"])
        c2 = getattr(events, params["coll2"])

        if params["coll1"] == params["coll2"]:
            obj1, obj2 = ak.unzip(ak.combinations(c1, 2))
        else:
            obj1, obj2 = ak.unzip(ak.cartesian([c1, c2]))

        dr = obj1.delta_r(obj2)
        mask = ak.any(dr > params["dr_min"], axis=1)
        return ak.where(ak.is_none(mask), False, mask)

    return Cut(
        name=f"{pair_str}_deltaR_gt_{dr_min}",
        params={"coll1": coll1, "coll2": coll2, "dr_min": dr_min},
        function=_impl,
    )


def _get_nObj_impl(events, params, **kwargs):
    return ak.num(getattr(events, params["coll"])) >= params["N"]

def get_nElectrons(N, coll):
    return Cut(
        name=f"nElectrons_min{N}",
        params={"N": N, "coll": coll},
        function=_get_nObj_impl
    )

def get_nMuons(N, coll):
    return Cut(
        name=f"nMuons_min{N}",
        params={"N": N, "coll": coll},
        function=_get_nObj_impl
    )

def get_d0_lt(coll, max_d0, lepton_index=0):
    def _impl(events, params, **kwargs):
        padded = ak.pad_none(getattr(events, params["coll"]), params["lepton_index"] + 1)
        lepton = padded[:, params["lepton_index"]]
        d0 = ak.fill_none(lepton.absd0_um, -1.0)
        return d0 < params["max_d0"]
    return Cut(
        name=f"{coll}_d0_lt_{max_d0}_lep{lepton_index}",
        params={"coll": coll, "max_d0": max_d0, "lepton_index": lepton_index},
        function=_impl
    )
