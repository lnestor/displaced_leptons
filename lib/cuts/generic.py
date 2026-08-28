import awkward as ak
import numpy as np
from pocket_coffea.lib.cut_definition import Cut


def _get_field_val(events, coll, field, pos):
    if pos is None:
        return getattr(getattr(events, coll), field)

    padded = ak.pad_none(getattr(events, coll), pos + 1)
    obj = padded[:, pos]
    return ak.fill_none(getattr(obj, field), np.nan)


def invert_cut(cut):
    """Negate another cut's mask.

    Wraps `cut` and returns a Cut whose mask is the logical NOT of it.
    Preserves whatever level (event or object) the wrapped cut operates at.
    """
    def _invert_impl(events, params, **kwargs):
        return ~cut.function(events, params=params, **kwargs)

    return Cut(
        name=f"not_{cut.name}",
        params=cut.params,
        function=_invert_impl,
        collection=cut.collection,
    )


def _val_between_impl(events, params, **kwargs):
    val = _get_field_val(events, params["coll"], params["field"], params["pos"])
    mask = (val > params["min"]) & (val < params["max"])
    return mask if params["pos"] is not None else ak.any(mask, axis=1)


def get_val_between(coll, field, min_val, max_val, pos=None):
    """Build an event level cut on `field` of objects in `coll`.

    If `pos` is None, the event passes if ANY object in `coll` has `field`
    strictly between `min_val` and `max_val`. If `pos` is given, only the
    object at that index (e.g. 0 for leading) is checked; events with fewer
    than `pos + 1` objects in `coll` fail the cut.
    """
    name = f"{coll}_{field}_between_{min_val}_{max_val}"
    if pos is not None:
        name += f"_pos{pos}"
    return Cut(
        name=name,
        params={"coll": coll, "field": field, "min": min_val, "max": max_val, "pos": pos},
        function=_val_between_impl,
    )


def _val_gt_impl(events, params, **kwargs):
    val = _get_field_val(events, params["coll"], params["field"], params["pos"])
    mask = val > params["val"]
    return mask if params["pos"] is not None else ak.any(mask, axis=1)


def get_val_gt(coll, field, val, pos=None):
    """Build an event level cut requiring `field` to be greater than `val`.

    Operates on objects in `coll`. See get_val_between for the `pos`
    semantics (any-object vs. fixed-index check).
    """
    name = f"{coll}_{field}_gt_{val}"
    if pos is not None:
        name += f"_pos{pos}"
    return Cut(
        name=name,
        params={"coll": coll, "field": field, "val": val, "pos": pos},
        function=_val_gt_impl,
    )


def _val_lt_impl(events, params, **kwargs):
    val = _get_field_val(events, params["coll"], params["field"], params["pos"])
    mask = val < params["val"]
    return mask if params["pos"] is not None else ak.any(mask, axis=1)


def get_val_lt(coll, field, val, pos=None):
    """Build an event level cut requiring `field` to be less than `val`.

    Operates on objects in `coll`. See get_val_between for the `pos`
    semantics (any-object vs. fixed-index check).
    """
    name = f"{coll}_{field}_lt_{val}"
    if pos is not None:
        name += f"_pos{pos}"
    return Cut(
        name=name,
        params={"coll": coll, "field": field, "val": val, "pos": pos},
        function=_val_lt_impl,
    )


def get_pt_gt(coll, val, pos=None):
    """Event level cut requiring pt of an object in `coll` to exceed `val`.

    See get_val_between for the `pos` semantics.
    """
    return get_val_gt(coll, "pt", val, pos=pos)


def get_pt_lt(coll, val, pos=None):
    """Event level cut requiring pt of an object in `coll` to be under `val`.

    See get_val_between for the `pos` semantics.
    """
    return get_val_lt(coll, "pt", val, pos=pos)


def get_d0_lt(coll, max_d0, pos=None):
    """Event level cut requiring |d0| of an object in `coll` to be under `max_d0`.

    `max_d0` is in um. See get_val_between for the `pos` semantics.
    """
    return get_val_lt(coll, "absd0_um", max_d0, pos=pos)


def get_d0_gt(coll, min_d0, pos=None):
    """Event level cut requiring |d0| of an object in `coll` to exceed `min_d0`.

    `min_d0` is in um. See get_val_between for the `pos` semantics.
    """
    return get_val_gt(coll, "absd0_um", min_d0, pos=pos)


def get_d0_between(coll, min_d0, max_d0, pos=None):
    """Event level cut requiring |d0| of an object in `coll` to be between
    `min_d0` and `max_d0`.

    Both bounds are in um. See get_val_between for the `pos` semantics.
    """
    return get_val_between(coll, "absd0_um", min_d0, max_d0, pos=pos)
