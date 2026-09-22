import awkward as ak
from pocket_coffea.workflows.base import BaseProcessorABC
from lib.workflow.supplement import SupplementPlugin


class AnalysisProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.output_format["supplement_diagnostics"] = {}


    def apply_object_preselection(self, variation):
        self._define_custom_fields(self.cfg.custom_fields.get("preselection", {}))
        self._apply_object_cuts()
        self._define_custom_fields(self.cfg.custom_fields.get("postselection", {}))


    def _define_custom_fields(self, fields):
        for fn in fields.get("common", []):
            fn(self.events, self._year, self._isMC, self._supplement.version)

        for fn in fields.get("bysample", {}).get(self._sample, []):
            fn(self.events, self._year, self._isMC, self._supplement.version)


    def _apply_object_cuts(self):
        for coll, cuts in self.cfg.object_selections.items():
            self.events[f"{coll}Good"] = self.events[coll][self._get_object_mask(coll, cuts)]


    def _get_object_mask(self, coll, cuts):
        mask = ak.ones_like(self.events[coll].pt, dtype=bool)
        for cut in cuts:
            mask = mask & cut.get_mask(
                self.events, self.params, year=self._year, sample=self._sample, isMC=self._isMC
            )
        return mask


    def count_objects(self, variation): # must be defined for PocketCoffea
        pass


    def load_metadata_extra(self):
        self._supplement = SupplementPlugin(
            self.cfg.supplements.get("skims" if self._isSkim else "jsons", []),
            self.events.metadata["das_names"],
            self.output["supplement_diagnostics"],
            self._dataset,
        )


    def process_extra_after_skim(self):
        trim_colls = ["Muon", "Electron"] if (self._year, self._sample) == ("2025", "EGamma") else None
        self.events = self._supplement.join(self.events, self.events.metadata["filename"], trim_colls)


    def get_preselection_mask(self, variation):
        combined = super().get_preselection_mask(variation)

        skim_mode = (self.workflow_options or {}).get("skim_mode", "skim")
        if (self._supplement.matched_mask is not None
                and self.cfg.save_skimmed_files
                and skim_mode == "presel_any_variation"):
            return self._supplement.expand_to_prejoin(combined)
        return combined


    def postprocess(self, accumulator):
        accumulator = super().postprocess(accumulator)
        print("\n" + SupplementPlugin.format_report(accumulator["supplement_diagnostics"]))
        return accumulator
