import awkward as ak
import numpy as np


class JoinMismatchError(Exception):
    def __init__(self, field, coll, row, key_values, left_count, right_count):
        self.field = field
        self.coll = coll
        self.row = row
        self.key_values = key_values
        self.left_count = left_count
        self.right_count = right_count
        super().__init__(
            f"join(): failed merging field '{field}' into collection '{coll}' at row {row}"
        )


def create_key(array, key_fields):
    return np.rec.fromarrays(
        [array[f] for f in key_fields],
        names=",".join(key_fields)
    )


def _match_keys(left_key, right_key):
    right_idx_candidate = np.searchsorted(right_key, left_key)
    right_idx_candidate = np.clip(right_idx_candidate, 0, len(right_key) - 1)

    matched_mask = right_key[right_idx_candidate] == left_key
    right_idx = right_idx_candidate[matched_mask]

    return right_idx, matched_mask


def match_indices(left, right, key_fields):
    """Match each row of left to a row of right by key_fields.

    Returns (right_idx, matched_mask): matched_mask marks which left rows
    found a match, right_idx (same length as left[matched_mask]) indexes
    into right for the matched rows.
    """
    left_key = create_key(left, key_fields)
    right_key = create_key(right, key_fields)

    if len(right_key) == 0:
        return np.array([], dtype=np.int64), np.zeros(len(left), dtype=bool)

    sort_order = np.argsort(right_key, order=key_fields)
    right_key = right_key[sort_order]

    matched_right_idx, matched_mask = _match_keys(left_key, right_key)
    return sort_order[matched_right_idx], matched_mask


def join(left, right, key_fields):
    right_mask = np.isin(create_key(right, key_fields), create_key(left, key_fields))
    right = right[right_mask]

    matched_right_idx, matched_mask = match_indices(left, right, key_fields)
    right_matched = right[matched_right_idx]

    left = left[matched_mask]

    new_collections = {}
    for field in right_matched.fields:
        if field in key_fields:
            continue

        coll, _, subfield = field.partition("_")

        # Counter branches (e.g. "nMuon") have no "_" separator -- skip them,
        # the jaggedness they encode is already carried by the sub-field arrays.
        if not subfield:
            continue

        if coll in left.fields:
            try:
                left[coll] = ak.with_field(left[coll], right_matched[field], subfield)
            except ValueError as e:
                left_counts = ak.to_numpy(ak.num(left[coll], axis=1))
                right_counts = ak.to_numpy(ak.num(right_matched[field], axis=1))
                mismatch_idx = np.flatnonzero(left_counts != right_counts)
                if len(mismatch_idx) == 0:
                    raise
                i = int(mismatch_idx[0])
                key_values = {k: left[k][i] for k in key_fields}
                raise JoinMismatchError(
                    field, coll, i, key_values, int(left_counts[i]), int(right_counts[i])
                ) from e
        else:
            new_collections.setdefault(coll, {})[subfield] = right_matched[field]

    for coll, subfields in new_collections.items():
        left[coll] = ak.zip(subfields)

    return left


