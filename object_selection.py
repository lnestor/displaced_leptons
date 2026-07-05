import awkward as ak
import numpy as np
from pocket_coffea.lib.cut_definition import Cut


def get_min_pt(coll, channel=None, min_pt=None):
    if channel is not None and min_pt is not None:
        raise ValueError("get_min_pt: specify only one of 'channel' or 'min_pt', not both")

    if channel is not None:
        def _impl(events, params, processor_params, year, **kwargs):
            pt = processor_params.object_selection[params["channel"]][params["coll"]][year].pt
            return events[params["coll"]].pt > pt
        return Cut(name=f"{coll}_minpt_{channel}", params={"coll": coll, "channel": channel}, function=_impl)

    elif min_pt is not None:
        def _impl(events, params, **kwargs):
            return events[params["coll"]].pt > params["pt"]
        return Cut(name=f"{coll}_minpt_{min_pt}", params={"coll": coll, "pt": min_pt}, function=_impl)

    else:
        raise ValueError("get_min_pt: must specify either 'channel' or 'min_pt'")

def get_max_eta(coll, channel=None, max_eta=None):
    if channel is not None and max_eta is not None:
        raise ValueError("get_max_eta: specify only one of 'channel' or 'max_eta', not both")

    if channel is not None:
        def _impl(events, params, processor_params, year, **kwargs):
            eta = processor_params.object_selection[params["channel"]][params["coll"]][year].eta
            return abs(events[params["coll"]].eta) < eta
        return Cut(name=f"{coll}_maxeta_{channel}", params={"coll": coll, "channel": channel}, function=_impl)

    elif max_eta is not None:
        def _impl(events, params, **kwargs):
            return abs(events[params["coll"]].eta) < params["eta"]
        return Cut(name=f"{coll}_maxeta_{max_eta}", params={"coll": coll, "eta": max_eta}, function=_impl)

    else:
        raise ValueError("get_max_eta: must specify either 'channel' or 'max_eta'")


def get_sc_gap_veto(coll):
    def _impl(events, params, **kwargs):
        obj = events[params["coll"]]
        return ~obj.is_gap
    return Cut(name=f"{coll}_sc_gap_veto", params={"coll": coll}, function=_impl)


def get_ele_tight_id(coll):
    def _impl(events, params, **kwargs):
        ALL_CUTS_TIGHT = 0b100100100100100100100100100100
        NO_ISO_MASK    = 0b111111000111111111111111111111
        obj = events[params["coll"]]
        return (obj.vidNestedWPBitmap & NO_ISO_MASK) == (ALL_CUTS_TIGHT & NO_ISO_MASK)
    return Cut(name=f"{coll}_id_tight", params={"coll": coll}, function=_impl)


def get_max_iso(coll, channel=None, iso_base=None, iso_pt_dep=None):
    if channel is not None and (iso_base is not None or iso_pt_dep is not None):
        raise ValueError("get_max_iso: specify only one of 'channel' or 'iso_base'/'iso_pt_dep', not both")

    if channel is not None:
        def _impl(events, params, processor_params, year, **kwargs):
            obj_params = processor_params.object_selection[params["channel"]][params["coll"]][year]
            obj = events[params["coll"]]
            return obj.customIso < obj_params.iso_base + obj_params.iso_pt_dep / obj.pt
        return Cut(name=f"{coll}_isolation_{channel}", params={"coll": coll, "channel": channel}, function=_impl)

    elif iso_base is not None and iso_pt_dep is not None:
        def _impl(events, params, **kwargs):
            obj = events[params["coll"]]
            return obj.customIso < params["iso_base"] + params["iso_pt_dep"] / obj.pt
        return Cut(
            name=f"{coll}_isolation_{iso_base}_{iso_pt_dep}",
            params={"coll": coll, "iso_base": iso_base, "iso_pt_dep": iso_pt_dep},
            function=_impl
        )

    else:
        raise ValueError("get_max_iso: must specify either 'channel' or both 'iso_base' and 'iso_pt_dep'")


def get_etaphi_veto(coll, channel=None, eta_min=None, eta_max=None, phi_min=None, phi_max=None):
    fixed_values = (eta_min, eta_max, phi_min, phi_max)
    if channel is not None and any(v is not None for v in fixed_values):
        raise ValueError("get_etaphi_veto: specify only one of 'channel' or 'eta_min'/'eta_max'/'phi_min'/'phi_max', not both")

    if channel is not None:
        def _impl(events, params, processor_params, year, **kwargs):
            veto_params = processor_params.object_selection[params["channel"]][params["coll"]][year].etaphi_veto
            obj = events[params["coll"]]
            in_veto = (
                (obj.eta > veto_params.eta_min) &
                (obj.eta < veto_params.eta_max) &
                (obj.phi > veto_params.phi_min) &
                (obj.phi < veto_params.phi_max)
            )
            return ~in_veto
        return Cut(name=f"{coll}_etaphi_veto_{channel}", params={"coll": coll, "channel": channel}, function=_impl)

    elif all(v is not None for v in fixed_values):
        def _impl(events, params, **kwargs):
            obj = events[params["coll"]]
            in_veto = (
                (obj.eta > params["eta_min"]) &
                (obj.eta < params["eta_max"]) &
                (obj.phi > params["phi_min"]) &
                (obj.phi < params["phi_max"])
            )
            return ~in_veto
        return Cut(
            name=f"{coll}_etaphi_veto_{eta_min}_{eta_max}_{phi_min}_{phi_max}",
            params={"coll": coll, "eta_min": eta_min, "eta_max": eta_max, "phi_min": phi_min, "phi_max": phi_max},
            function=_impl
        )

    else:
        raise ValueError("get_etaphi_veto: must specify either 'channel' or all of 'eta_min', 'eta_max', 'phi_min', 'phi_max'")


def get_muon_tight_id(coll):
    def _impl(events, params, **kwargs):
        return events[params["coll"]].tightId == True
    return Cut(name=f"{coll}_id_tight", params={"coll": coll}, function=_impl)

