from pocket_coffea.parameters.cuts import passthrough

from lib.cuts.generic import (
    get_val_lt,
    get_val_gt,
    get_val_between,
    get_pt_lt,
    get_pt_gt,
    get_d0_lt,
    get_d0_gt,
    get_d0_between,
)


def _get_coll_from_channel(channel):
    if channel == "ee":
        return "ElectronGood", "ElectronGood", 0, 1
    elif channel == "mumu":
        return "MuonGood", "MuonGood", 0, 1
    elif channel == "emu":
        return "ElectronGood", "MuonGood", 0, 0
    else:
        raise ValueError(f"Channel {channel} is not valid.")


def _sweep_cats(prefix, coll1, idx1, coll2, idx2, field, sweep_edges, other_edges):
    other_lo, other_mid, other_hi = other_edges

    other_prompt = get_val_between(coll2, field, other_lo, other_mid, pos=idx2)
    other_mid_range = get_val_between(coll2, field, other_mid, other_hi, pos=idx2)

    cats = {
        f"{prefix}_a": [get_val_between(coll1, field, sweep_edges[0], sweep_edges[1], pos=idx1), other_prompt],
        f"{prefix}_b": [get_val_between(coll1, field, sweep_edges[0], sweep_edges[1], pos=idx1), other_mid_range],
    }

    for i in range(1, len(sweep_edges) - 1):
        low = sweep_edges[i]
        high = sweep_edges[i + 1]
        cats[f"{prefix}_c{i}"] = [get_val_between(coll1, field, low, high, pos=idx1), other_prompt]
        cats[f"{prefix}_d{i}"] = [get_val_between(coll1, field, low, high, pos=idx1), other_mid_range]

    return cats


def get_closure_test_cats(
    channel,
    field,
    sweep_edges,
    sweep_other_edges,
    point_edges,
    point_other_edges
):
    coll1, coll2, idx1, idx2 = _get_coll_from_channel(channel)

    point_lo, point_mid, point_hi = point_edges
    point_other_lo, point_other_mid, point_other_tail = point_other_edges

    lep1_point_near = get_val_between(coll1, field, point_lo, point_mid, pos=idx1)
    lep1_point_far = get_val_between(coll1, field, point_mid, point_hi, pos=idx1)
    lep2_point_near = get_val_between(coll2, field, point_lo, point_mid, pos=idx2)
    lep2_point_far = get_val_between(coll2, field, point_mid, point_hi, pos=idx2)

    lep1_other_prompt = get_val_between(coll1, field, point_other_lo, point_other_mid, pos=idx1)
    lep1_other_tail = get_val_gt(coll1, field, point_other_tail, pos=idx1)
    lep2_other_prompt = get_val_between(coll2, field, point_other_lo, point_other_mid, pos=idx2)
    lep2_other_tail = get_val_gt(coll2, field, point_other_tail, pos=idx2)

    cats = {
        **_sweep_cats("closure_sweep_l1", coll1, idx1, coll2, idx2, field, sweep_edges, sweep_other_edges),
        **_sweep_cats("closure_sweep_l2", coll2, idx2, coll1, idx1, field, sweep_edges, sweep_other_edges),
        "closure_point_l1_a": [lep1_point_near, lep2_other_prompt],
        "closure_point_l1_b": [lep1_point_near, lep2_other_tail],
        "closure_point_l1_c": [lep1_point_far, lep2_other_prompt],
        "closure_point_l1_d": [lep1_point_far, lep2_other_tail],
        "closure_point_l2_a": [lep2_point_near, lep1_other_prompt],
        "closure_point_l2_b": [lep2_point_near, lep1_other_tail],
        "closure_point_l2_c": [lep2_point_far, lep1_other_prompt],
        "closure_point_l2_d": [lep2_point_far, lep1_other_tail],
    }

    return cats


def get_baseline_cat():
    return { "baseline": [passthrough] }


def get_pcr_cat(channel, field, threshold):
    coll1, coll2, idx1, idx2 = _get_coll_from_channel(channel)

    return {
        f"pcr_{field}": [get_val_lt(coll1, field, threshold, pos=idx1), get_val_lt(coll2, field, threshold, pos=idx2)]
    }


def get_abcd_cats(channel, field, threshold, sr_split=None, pt_split=None):
    coll1, coll2, idx1, idx2 = _get_coll_from_channel(channel)
    pt_coll = "ElectronGood" if channel == "ee" else "MuonGood"

    lep1_below = get_val_lt(coll1, field, threshold, pos=idx1)
    lep1_above = get_val_gt(coll1, field, threshold, pos=idx1)
    lep2_below = get_val_lt(coll2, field, threshold, pos=idx2)
    lep2_above = get_val_gt(coll2, field, threshold, pos=idx2)

    cats = {
        f"abcd_{field}_a": [lep1_below, lep2_below],
        f"abcd_{field}_b": [lep1_above, lep2_below],
        f"abcd_{field}_c": [lep1_below, lep2_above],
        f"abcd_{field}_d": [lep1_above, lep2_above],
    }

    if sr_split is not None:
        lep1_between = get_val_between(coll1, field, threshold, sr_split, pos=idx1)
        lep1_high = get_val_gt(coll1, field, sr_split, pos=idx1)
        lep2_between = get_val_between(coll2, field, threshold, sr_split, pos=idx2)
        lep2_high = get_val_gt(coll2, field, sr_split, pos=idx2)

        cats[f"abcd_{field}_b1"] = [lep1_between, lep2_below]
        cats[f"abcd_{field}_b2"] = [lep1_high, lep2_below]
        cats[f"abcd_{field}_c1"] = [lep1_below, lep2_between]
        cats[f"abcd_{field}_c2"] = [lep1_below, lep2_high]
        cats[f"abcd_{field}_d1"] = [lep1_between, lep2_between]
        cats[f"abcd_{field}_d2"] = [lep1_high, lep2_between]
        cats[f"abcd_{field}_d3"] = [lep1_between, lep2_high]
        cats[f"abcd_{field}_d4"] = [lep1_high, lep2_high]

        if pt_split is not None:
            lowpt = get_pt_lt(pt_coll, pt_split, pos=0)
            highpt = get_pt_gt(pt_coll, pt_split, pos=0)

            cats[f"abcd_{field}_b1_lowpt"] = [lep1_between, lep2_below, lowpt]
            cats[f"abcd_{field}_b1_highpt"] = [lep1_between, lep2_below, highpt]
            cats[f"abcd_{field}_c1_lowpt"] = [lep1_below, lep2_between, lowpt]
            cats[f"abcd_{field}_c1_highpt"] = [lep1_below, lep2_between, highpt]
            cats[f"abcd_{field}_d1_lowpt"] = [lep1_between, lep2_between, lowpt]
            cats[f"abcd_{field}_d1_highpt"] = [lep1_between, lep2_between, highpt]

    return cats
