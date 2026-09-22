import json
import os

import awkward as ak
import numpy as np
import uproot

import lib.awkward_helper as ak_help

TREE_NAME = "supplementTree/Events"
LUMI_FIELDS = ["run", "luminosityBlock"]
EVENT_FIELDS = ["run", "luminosityBlock", "event"]


class SupplementPlugin:
    def __init__(self, json_paths, das_names, diagnostics, dataset):
        self.files = {}
        self.version = 0
        self.matched_mask = None
        self._diag = None

        self._load_definitions(json_paths, das_names)

        if self.version != 0:
            self._diag = diagnostics.setdefault(dataset, {
                "chunks_with_supplement_file": 0,
                "chunks_without_supplement_file": 0,
                "events_matched": 0,
                "events_unmatched": 0,
                "events_without_supplement_file": 0,
            })

    def join(self, events, central_filename, trim_colls=None):
        if self.version == 0:
            return events

        central_lfn = "/store/" + central_filename.split("/store/", 1)[1]
        files = self.files.get(central_lfn, [])

        if not files:
            self._diag["chunks_without_supplement_file"] += 1
            self._diag["events_without_supplement_file"] += len(events)
            return self._join_without_file(events)

        supplement = self._load_for_chunk(files, events)

        if trim_colls:
            events, supplement = ak_help.trim_to_shortest(
                events, supplement, colls=trim_colls, key_fields=EVENT_FIELDS
            )

        _, self.matched_mask = ak_help.match_indices(events, supplement, EVENT_FIELDS)

        n_before_join = len(events)
        try:
            events = ak_help.join(events, supplement, EVENT_FIELDS)
        except ak_help.JoinMismatchError as e:
            raise ValueError(
                f"Supplement join failed: {e.key_values} has {e.left_count} '{e.coll}' objects "
                f"in the central file but {e.right_count} in the supplement file"
            ) from e

        self._diag["chunks_with_supplement_file"] += 1
        self._diag["events_matched"] += len(events)
        self._diag["events_unmatched"] += n_before_join - len(events)

        return events

    def expand_to_prejoin(self, mask):
        full = np.zeros(len(self.matched_mask), dtype=bool)
        full[self.matched_mask] = ak.to_numpy(mask)
        return full

    @staticmethod
    def format_report(diagnostics):
        lines = ["[Supplement matching diagnostics]"]
        for dataset, diag in diagnostics.items():
            chunks_with = diag["chunks_with_supplement_file"]
            chunks_without = diag["chunks_without_supplement_file"]
            events_matched = diag["events_matched"]
            events_unmatched = diag["events_unmatched"]
            events_without = diag["events_without_supplement_file"]
            events_total = events_matched + events_unmatched + events_without
            pct = 100 * events_matched / events_total if events_total else 0.0

            lines.append(f"  {dataset}:")
            lines.append(f"    {chunks_without}/{chunks_with + chunks_without} chunks had no supplement file")
            lines.append(f"    {events_matched}/{events_total} events matched ({pct:.1f}%): "
                         f"{events_unmatched} unmatched, {events_without} in chunks without a supplement file")
        return "\n".join(lines)

    def _load_definitions(self, json_paths, das_names):
        matched_json = None

        for json_path in json_paths:
            with open(self._resolve_json_path(json_path)) as f:
                supp_dict = json.load(f)

            for supp in supp_dict.values():
                metadata = supp["metadata"]
                supp_datasets = metadata["dataset"]
                if not isinstance(supp_datasets, list):
                    supp_datasets = [supp_datasets]

                if not any(d in das_names for d in supp_datasets):
                    continue

                if matched_json is not None:
                    raise ValueError(
                        f"Multiple supplement entries match dataset {das_names}: "
                        f"found in both {matched_json} and {json_path}"
                    )
                matched_json = json_path
                self.files = supp["files"]
                self.version = metadata["version"]

    def _join_without_file(self, events):
        self.matched_mask = np.zeros(len(events), dtype=bool)
        events = events[:0]

        schema_file = next((f for files in self.files.values() for f in files), None)
        if schema_file is not None:
            events = ak_help.join(events, self._empty_schema(schema_file), EVENT_FIELDS)

        return events

    def _load_for_chunk(self, files, events):
        chunk_key = ak_help.create_key(events, LUMI_FIELDS)

        parts = []
        for path in files:
            with uproot.open(path) as root_file:
                tree = root_file[TREE_NAME]
                index = tree.arrays(LUMI_FIELDS)
                mask = np.isin(ak_help.create_key(index, LUMI_FIELDS), chunk_key)
                if mask.any():
                    parts.append(ak.packed(tree.arrays()[mask]))

        if parts:
            return ak.concatenate(parts)
        return self._empty_schema(files[0])

    @staticmethod
    def _resolve_json_path(json_path):
        # LPCCondorCluster ships transfer_input_files flat into the worker's working directory
        if os.path.exists(json_path):
            return json_path
        return json_path.rsplit("/datasets/", 1)[-1]

    @staticmethod
    def _empty_schema(path):
        with uproot.open(path) as root_file:
            return root_file[TREE_NAME].arrays(entry_stop=0)
