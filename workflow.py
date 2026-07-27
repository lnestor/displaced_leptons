import awkward as ak
import numpy as np
from coffea.analysis_tools import PackedSelection
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
import json
import os
from lib.object_cutflow import ObjectCutflow
from lib.named_cut import NamedCut
import lib.awkward_helper as ak_help

CENTRAL_NANOAOD_FLAG = 0

RUN_2_YEARS = ['2016_PreVFP', '2016_PostVFP', '2017', '2018']

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.output_format["cutflow_cumulative"] = {
            "initial": {},
            "skim": {},
            "preselection": {},
            "object_selection": {},
            **{cat: {} for cat in self._categories}
        }
        self.output_format["missing_events"] = {}


    def apply_object_preselection(self, variation):
        self._define_custom_fields()
        self._apply_object_cuts(variation)


    def _define_custom_fields(self):
        for fn in self.cfg.custom_fields:
            fn(self.events, self._year, self._isMC, self._supplement_version)


    def _apply_object_cuts(self, variation):
        for coll, selection in self.cfg.object_selections.items():
            cutflow = ObjectCutflow(collection=coll, cuts=selection["cuts"])
            cutflow.run(self.events, self.params, year=self._year, sample=self._sample, isMC=self._isMC)

            self.events[f"{coll}Good"] = self.events[coll][cutflow.get_final_object_mask()]

            if "min" in selection:
                obj_sel = self.output["cutflow_cumulative"]["object_selection"]
                event_cumul = ak.ones_like(self.events.event, dtype=bool)

                for i in range(len(cutflow)):
                    event_cumul = event_cumul & cutflow.get_event_mask(i, selection["min"])
                    count = int(ak.sum(event_cumul))
                    obj_sel.setdefault(cutflow.cuts[i].label, {}).setdefault(self._dataset, {})[variation] = count

                self.events = self.events[event_cumul]


    def count_objects(self, variation):
        pass


    def load_metadata_extra(self):
        self._supplement_files = {}
        self._supplement_version = 0

        matched_json = None
        for supplement_json in self.cfg.supplements:
            # When running on condor, supplement_json lands in the root directory, not under a subdirectory
            path = supplement_json if os.path.exists(supplement_json) else os.path.basename(supplement_json)
            supp_dict = json.load(open(path))

            for supp in supp_dict.values():
                metadata = supp["metadata"]
                if metadata["sample"] != self._sample or metadata["year"] != self._year or metadata["era"] != self._era:
                    continue

                if matched_json is not None:
                    raise ValueError(
                        f"Multiple supplement entries match sample '{self._sample}', "
                        f"year '{self._year}': found in both {matched_json} and {supplement_json}"
                    )
                matched_json = supplement_json

                self._supplement_files = supp["files"]
                self._supplement_version = metadata["version"]


    def process_extra_after_skim(self):
        central_lfn = "/store/" + self.events.metadata["filename"].split("/store/", 1)[1]
        supplement_files = self._supplement_files.get(central_lfn, [])

        if not supplement_files:
            if self._supplement_version != 0:
                raise ValueError(
                    f"Dataset '{self._dataset}' expects supplement coverage (version "
                    f"{self._supplement_version}) but no supplement file was found for "
                    f"'{central_lfn}'"
                )
            return

        chunk_lumis = set(zip(
            self.events["run"].tolist(), self.events["luminosityBlock"].tolist()
        ))

        supplement_parts = []
        for f in supplement_files:
            tree = uproot.open(f)["supplementTree/Events"]
            index = tree.arrays(["run", "luminosityBlock"])
            mask = np.fromiter(
                ((r, l) in chunk_lumis for r, l in zip(
                    index["run"].tolist(), index["luminosityBlock"].tolist()
                )),
                dtype=bool, count=len(index)
            )
            if not mask.any():
                continue
            supplement_parts.append(tree.arrays()[mask])

        if not supplement_parts:
            n_before_join = len(self.events)
            self.events = self.events[np.zeros(n_before_join, dtype=bool)]
            n_missing = n_before_join
            self.output["missing_events"][self._dataset] = n_missing
            self.output["cutflow_cumulative"]["initial"][self._dataset] = self.nEvents_initial - n_missing

            names = list(self._skim_masks.names)
            for i, cut_name in enumerate(names):
                cumul = ak.sum(self._skim_masks.all(*names[:i+1]))
                short_name = cut_name.split("__")[0]
                self.output["cutflow_cumulative"]["skim"].setdefault(short_name, {})[self._dataset] = cumul
            return

        supplement = ak.concatenate(supplement_parts)

        n_before_join = len(self.events)
        self.events = ak_help.join(self.events, supplement, ["run", "luminosityBlock", "event"])
        n_after_join = len(self.events)
        n_missing = n_before_join - n_after_join

        self.output["missing_events"][self._dataset] = n_missing
        self.output["cutflow_cumulative"]["initial"][self._dataset] = self.nEvents_initial - n_missing

        names = list(self._skim_masks.names)
        for i, cut_name in enumerate(names):
            cumul = ak.sum(self._skim_masks.all(*names[:i+1]))
            short_name = cut_name.split("__")[0]
            self.output["cutflow_cumulative"]["skim"].setdefault(short_name, {})[self._dataset] = cumul


    def process_extra_after_presel(self, variation):
        names = list(self._presel_masks.names)
        for i, cut_name in enumerate(names):
            cumul = ak.sum(self._presel_masks.all(*names[:i+1]))
            short_name = cut_name.split("__")[0]
            self.output["cutflow_cumulative"]["preselection"] \
                .setdefault(short_name, {}) \
                .setdefault(self._dataset, {})[variation] = cumul


    def get_preselection_mask(self, variation):
        self._presel_masks = PackedSelection()
        for cut in self._preselections:
            mask = cut.get_mask(
                self.events,
                processor_params=self.params,
                year=self._year,
                sample=self._sample,
                isMC=self._isMC
            )
            self._presel_masks.add(cut.id, mask)
        return self._presel_masks.all(*self._presel_masks.names)


    def postprocess(self, accumulator):
        accumulator = super().postprocess(accumulator)
        accumulator["cut_labels"] = {
            "skim": [getattr(cut, "label", cut.name) for cut in self.cfg.skim],
            "preselection": [getattr(cut, "label", cut.name) for cut in self.cfg.preselections],
            "object_selection": list(accumulator["cutflow_cumulative"]["object_selection"].keys()),
            **{
                category: [getattr(cut, "label", cut.name) for cut in cuts]
                for category, cuts in self.cfg.categories_cfg.items()
            }
        }

        for stage in accumulator["cut_labels"].keys():
            accumulator["cut_labels"][stage] = [
                label for label in accumulator["cut_labels"][stage]
                if label != "passthrough"
            ]

            if "passthrough" in accumulator["cutflow_cumulative"][stage]:
                del accumulator["cutflow_cumulative"][stage]["passthrough"]

        return accumulator


    def count_events(self, variation):
        super().count_events(variation)

        for category, cuts in self.cfg.categories_cfg.items():
            cut_ids = [cut.id for cut in cuts]
            for i, cut in enumerate(cuts):
                mask = self._categories.storage.all(cut_ids[:i+1])
                if self._categories.is_multidim and mask.ndim > 1:
                    mask = ak.any(mask, axis=1)

                self.output["cutflow_cumulative"][category] \
                    .setdefault(cut.name, {}) \
                    .setdefault(self._dataset, {}) \
                    .setdefault(self._sample, {})[variation] = ak.sum(mask)

