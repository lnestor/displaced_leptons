import awkward as ak
import numpy as np
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
import json
import os
import lib.awkward_helper as ak_help

# To calculate nSupplementMuon/nSupplementElectron, choose an arbitrary field
# from both to run ak.num() on since supplement files don't have nMuon/nElectron
SUPPLEMENT_MUON_COUNT_FIELD = "Muon_pfIso04_sumChargedHadronPt"
SUPPLEMENT_ELECTRON_COUNT_FIELD = "Electron_pfIso03_sumChargedHadronPt"
SUPPLEMENT_KEY_FIELDS = ["run", "luminosityBlock", "event"]
SUPPLEMENT_BRANCHES = SUPPLEMENT_KEY_FIELDS + [SUPPLEMENT_MUON_COUNT_FIELD, SUPPLEMENT_ELECTRON_COUNT_FIELD]


class JoinDiagnosticProcessor(BaseProcessorABC):
    def apply_object_preselection(self, variation):
        pass


    def count_objects(self, variation):
        pass


    def load_metadata_extra(self):
        self._supplement_files = {}
        self._supplement_version = 0

        das_names = self.events.metadata["das_names"]

        matched_json = None
        for supplement_json in self.cfg.supplements:
            # LPCCondorCluster ships transfer_input_files flat into the worker's
            # working directory, not preserving the original relative path.
            path = supplement_json if os.path.exists(supplement_json) else os.path.basename(supplement_json)
            with open(path) as f:
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
                        f"Multiple supplement entries match dataset for sample '{self._sample}', "
                        f"year '{self._year}': found in both {matched_json} and {supplement_json}"
                    )
                matched_json = supplement_json

                self._supplement_files = supp["files"]
                self._supplement_version = metadata["version"]


    def process_extra_after_skim(self):
        # Coffea consumes the nMuon/nElectron fields, so need to redefine them
        self.events["nMuon"] = ak.num(self.events.Muon)
        self.events["nElectron"] = ak.num(self.events.Electron)

        central_lfn = "/store/" + self.events.metadata["filename"].split("/store/", 1)[1]
        supplement_files = self._supplement_files.get(central_lfn, [])

        if supplement_files:
            supplement = ak.concatenate([
                uproot.open(f)["supplementTree/Events"].arrays(SUPPLEMENT_BRANCHES)
                for f in supplement_files
            ])
        else:
            supplement = ak.Array({
                **{f: [] for f in SUPPLEMENT_KEY_FIELDS},
                SUPPLEMENT_MUON_COUNT_FIELD: ak.Array([[]])[:0],
                SUPPLEMENT_ELECTRON_COUNT_FIELD: ak.Array([[]])[:0],
            })

        supplement_n_muon = ak.num(supplement[SUPPLEMENT_MUON_COUNT_FIELD])
        supplement_n_electron = ak.num(supplement[SUPPLEMENT_ELECTRON_COUNT_FIELD])

        supplement_idx, matched_mask = ak_help.match_indices(self.events, supplement, SUPPLEMENT_KEY_FIELDS)
        matched_mask = np.asarray(matched_mask)

        n_supplement_muon = np.full(len(self.events), -1, dtype=np.int64)
        n_supplement_electron = np.full(len(self.events), -1, dtype=np.int64)
        n_supplement_muon[matched_mask] = np.asarray(supplement_n_muon)[supplement_idx]
        n_supplement_electron[matched_mask] = np.asarray(supplement_n_electron)[supplement_idx]

        muon_diff = np.where(matched_mask, np.asarray(self.events.nMuon) - n_supplement_muon, np.nan)
        electron_diff = np.where(matched_mask, np.asarray(self.events.nElectron) - n_supplement_electron, np.nan)

        self.events["nSupplementMuon"] = n_supplement_muon
        self.events["nSupplementElectron"] = n_supplement_electron
        self.events["muonCountDiff"] = muon_diff
        self.events["electronCountDiff"] = electron_diff
