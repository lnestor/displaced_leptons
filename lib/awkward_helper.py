import awkward as ak
import numpy as np


# _KEY_FIELD_BITS = {
#     "event": 31,
#     "luminosityBlock": 14,
#     "run": 19,
# }
#
#
# def create_key(array, key_fields):
#     packed = np.zeros(len(array), dtype=np.uint64)
#     for field in key_fields:
#         bits = _KEY_FIELD_BITS[field]
#         values = ak.to_numpy(array[field]).astype(np.uint64)
#         if values.size and int(values.max()) >= (1 << bits):
#             raise ValueError(
#                 f"create_key: '{field}' value {int(values.max())} exceeds the "
#                 f"{bits}-bit budget reserved for it in _KEY_FIELD_BITS"
#             )
#         packed = (packed << np.uint64(bits)) | values
#     return packed


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


def join(left, right, key_fields):
    left_key = create_key(left, key_fields)
    right_key = create_key(right, key_fields)

    right_mask = np.isin(right_key, left_key)
    right_key = right_key[right_mask]
    right = right[right_mask]

    # Even with no overlap, right_matched must retain right's field schema so the
    # fields get added (as empty arrays) below -- otherwise callers expecting
    # e.g. left.Electron.some_joined_field see no such field at all, instead of
    # an empty one, whenever a chunk happens to have zero matching rows.
    if len(right_key) == 0:
        matched_mask = np.zeros(len(left), dtype=bool)
        right_matched = right
    else:
        sort_order = np.argsort(right_key, order=key_fields)
        right_key = right_key[sort_order]
        right = right[sort_order]

        matched_right_idx, matched_mask = _match_keys(left_key, right_key)
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
            left[coll] = ak.with_field(left[coll], right_matched[field], subfield)
        else:
            new_collections.setdefault(coll, {})[subfield] = right_matched[field]

    for coll, subfields in new_collections.items():
        left[coll] = ak.zip(subfields)

    return left


