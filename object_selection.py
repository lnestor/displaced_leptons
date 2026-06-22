import awkward as ak
import numpy as np
from pocket_coffea.lib.cut_definition import Cut


def min_pt(collection, pt):
    def _impl(events, params, **kwargs):
        return events[params["collection"]].pt > params["pt"]
    return Cut(name=f"{collection}_minpt_{pt}", params={"collection": collection, "pt": pt}, function=_impl)


def max_eta(collection, eta):
    def _impl(events, params, **kwargs):
        return abs(events[params["collection"]].eta) < params["eta"]
    return Cut(name=f"{collection}_maxeta_{eta}", params={"collection": collection, "eta": eta}, function=_impl)


def eta_phi_veto(collection, eta_min, eta_max, phi_min, phi_max):
    def _impl(events, params, **kwargs):
        obj = events[params["collection"]]
        in_veto = (
            (obj.eta > params["eta_min"]) &
            (obj.eta < params["eta_max"]) &
            (obj.phi > params["phi_min"]) &
            (obj.phi < params["phi_max"])
        )
        return ~in_veto
    return Cut(
        name=f"{collection}_etaphi_veto",
        params={"collection": collection, "eta_min": eta_min, "eta_max": eta_max, "phi_min": phi_min, "phi_max": phi_max},
        function=_impl
    )


def isolation(collection, iso_base, iso_pt_dep):
    def _impl(events, params, **kwargs):
        obj = events[params["collection"]]
        return obj.customIso < params["iso_base"] + params["iso_pt_dep"] / obj.pt
    return Cut(
        name=f"{collection}_isolation",
        params={"collection": collection, "iso_base": iso_base, "iso_pt_dep": iso_pt_dep},
        function=_impl
    )


def lepton_id(collection, id_field, id_req):
    def _impl(events, params, **kwargs):
        return events[params["collection"]][params["id_field"]] == params["id_req"]
    return Cut(
        name=f"{collection}_id_{id_field}",
        params={"collection": collection, "id_field": id_field, "id_req": id_req},
        function=_impl
    )


def sc_gap_veto(collection):
    def _impl(events, params, **kwargs):
        obj = events[params["collection"]]
        eta_sc = abs(obj.deltaEtaSC + obj.eta)
        return ~((eta_sc >= 1.442) & (eta_sc <= 1.566))
    return Cut(name=f"{collection}_sc_gap_veto", params={"collection": collection}, function=_impl)

