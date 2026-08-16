from pocket_coffea.parameters.cuts import passthrough

from event_selection import (
    get_d0_lt,
    get_d0_gt,
    get_val_between,
    get_d0_between,
    get_leading_minpt,
    get_leading_maxpt,
)

CLOSURE_D0_SWEEP_VALS = [30, 40, 50, 60, 70, 80, 90, 100]


def _get_coll_from_channel(channel):
    if channel == "ee":
        return "ElectronGood", "ElectronGood", 0, 1
    elif channel == "mumu":
        return "MuonGood", "MuonGood", 0, 1
    elif channel == "emu":
        return "ElectronGood", "MuonGood", 0, 0
    else:
        raise ValueError(f"Channel {channel} is not valid.")


def _sweep_cats(prefix, coll1, idx1, coll2, idx2, field):
    cats = {
        f"{prefix}_a": [get_val_between(coll1, field, 20, 30, pos=idx1), get_val_between(coll2, field, 20, 100, pos=idx2)],
        f"{prefix}_b": [get_val_between(coll1, field, 20, 30, pos=idx1), get_val_between(coll2, field, 100, 500, pos=idx2)],
    }

    for i in range(len(CLOSURE_D0_SWEEP_VALS) - 1):
        low = CLOSURE_D0_SWEEP_VALS[i]
        high = CLOSURE_D0_SWEEP_VALS[i + 1]
        cats[f"{prefix}_c{i + 1}"] = [get_val_between(coll1, field, low, high, pos=idx1), get_val_between(coll2, field, 20, 100, pos=idx2)]
        cats[f"{prefix}_d{i + 1}"] = [get_val_between(coll1, field, low, high, pos=idx1), get_val_between(coll2, field, 100, 500, pos=idx2)]

    return cats


def get_closure_test_cats(channel, field):
    coll1, coll2, idx1, idx2 = _get_coll_from_channel(channel)

    cats = {
        **_sweep_cats("closure_low_leptona_prompt", coll1, idx1, coll2, idx2, field),
        **_sweep_cats("closure_low_leptonb_prompt", coll2, idx2, coll1, idx1, field),
        "closure_high_leptona_prompt_a": [get_val_between(coll1, field, 20, 30, pos=idx1), get_val_between(coll2, field, 20, 100, pos=idx2)],
        "closure_high_leptona_prompt_b": [get_val_between(coll1, field, 20, 30, pos=idx1), get_val_between(coll2, field, 500, 100000, pos=idx2)],
        "closure_high_leptona_prompt_c": [get_val_between(coll1, field, 30, 100, pos=idx1), get_val_between(coll2, field, 20, 100, pos=idx2)],
        "closure_high_leptona_prompt_d": [get_val_between(coll1, field, 30, 100, pos=idx1), get_val_between(coll2, field, 500, 100000, pos=idx2)],
        "closure_high_leptonb_prompt_a": [get_val_between(coll2, field, 20, 30, pos=idx2), get_val_between(coll1, field, 20, 100, pos=idx1)],
        "closure_high_leptonb_prompt_b": [get_val_between(coll2, field, 20, 30, pos=idx2), get_val_between(coll1, field, 500, 100000, pos=idx1)],
        "closure_high_leptonb_prompt_c": [get_val_between(coll2, field, 30, 100, pos=idx2), get_val_between(coll1, field, 20, 100, pos=idx1)],
        "closure_high_leptonb_prompt_d": [get_val_between(coll2, field, 30, 100, pos=idx2), get_val_between(coll1, field, 500, 100000, pos=idx1)],
    }

    return cats


def get_default_cats(channel, only=[]):
    coll1, coll2, idx1, idx2 = _get_coll_from_channel(channel)
    pt_coll = "ElectronGood" if channel == "ee" else "MuonGood"

    cats = {
        "baseline": [passthrough],
        "pcr": [get_d0_lt(coll1, 50, idx1), get_d0_lt(coll2, 50, idx2)],
        "a": [get_d0_lt(coll1, 100, idx1), get_d0_lt(coll2, 100, idx2)],
        "b": [get_d0_gt(coll1, 100, idx1), get_d0_lt(coll2, 100, idx2)],
        "b_lowd0_lowpt": [get_d0_between(coll1, 100, 500, idx1), get_d0_lt(coll2, 100, idx2), get_leading_maxpt(pt_coll, channel=channel)],
        "b_lowd0_highpt": [get_d0_between(coll1, 100, 500, idx1), get_d0_lt(coll2, 100, idx2), get_leading_minpt(pt_coll, channel=channel)],
        "b_highd0": [get_d0_gt(coll1, 500, idx1), get_d0_lt(coll2, 100, idx2)],
        "c": [get_d0_lt(coll1, 100, idx1), get_d0_gt(coll2, 100, idx2)],
        "c_lowd0_lowpt": [get_d0_lt(coll1, 100, idx1), get_d0_between(coll2, 100, 500, idx2), get_leading_maxpt(pt_coll, channel=channel)],
        "c_lowd0_highpt": [get_d0_lt(coll1, 100, idx1), get_d0_between(coll2, 100, 500, idx2), get_leading_minpt(pt_coll, channel=channel)],
        "c_highd0": [get_d0_lt(coll1, 500, idx1), get_d0_gt(coll2, 100, idx2)],
        "sr1_lowpt": [get_d0_between(coll1, 100, 500, idx1), get_d0_between(coll2, 100, 500, idx2), get_leading_maxpt(pt_coll, channel=channel)],
        "sr1_highpt": [get_d0_between(coll1, 100, 500, idx1), get_d0_between(coll2, 100, 500, idx2), get_leading_minpt(pt_coll, channel=channel)],
        "sr2": [get_d0_gt(coll1, 500, idx1), get_d0_between(coll2, 100, 500, idx2)],
        "sr3": [get_d0_between(coll1, 100, 500, idx1), get_d0_gt(coll2, 500, idx2)],
        "sr4": [get_d0_gt(coll1, 500, idx1), get_d0_gt(coll2, 500, idx2)],
    }

    if len(only) > 0:
        return {k: v for k, v in cats.items() if k in only}
    else:
        return cats
