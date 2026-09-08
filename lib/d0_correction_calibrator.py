import os

import awkward as ak
import numpy as np
import correctionlib

from pocket_coffea.lib.calibrators.calibrator import Calibrator


def _evaluate_jagged(corr, values, variation):
    flat_values = np.asarray(ak.to_numpy(ak.flatten(values)), dtype=np.float64)
    flat_out = corr.evaluate(variation, flat_values)
    return ak.unflatten(flat_out, ak.num(values))


class D0CorrectionCalibrator(Calibrator):
    name = "d0_correction_calibrator"
    has_variations = True
    isMC_only = True
    calibrated_collections = ["Electron.dxybs", "Electron.dxybs_original", "Muon.dxybs", "Muon.dxybs_original"]

    def __init__(self, params, metadata, do_variations, **kwargs):
        super().__init__(params, metadata, do_variations, **kwargs)
        self.year = metadata["year"]
        # LPCCondorCluster ships transfer_input_files flat into the worker's
        # working directory, not preserving the original relative path.
        correction_file = self.params.d0_correction.file
        if not os.path.exists(correction_file):
            correction_file = os.path.basename(correction_file)
        self.cset = correctionlib.CorrectionSet.from_file(correction_file)

        self.electron_correction_name = f"electron_d0_correction_{self.year}"
        self.muon_correction_name = f"muon_d0_correction_{self.year}"
        self.correct_electron = self.electron_correction_name in self.cset
        self.correct_muon = self.muon_correction_name in self.cset

        # Calibrator.variations requires self._variations to be set
        self._variations = []
        if self.correct_electron:
            self._variations += ["electron_d0_correctionUp", "electron_d0_correctionDown"]
        if self.correct_muon:
            self._variations += ["muon_d0_correctionUp", "muon_d0_correctionDown"]

    def initialize(self, events):
        self.electron_dxybs_original = events.Electron.dxybs
        self.muon_dxybs_original = events.Muon.dxybs

        if self.correct_electron:
            corr = self.cset[self.electron_correction_name]
            self.electron_dxybs = {
                var: _evaluate_jagged(corr, events.Electron.dxybs, var)
                for var in ("nom", "up", "down")
            }
        else:
            self.electron_dxybs = dict.fromkeys(("nom", "up", "down"), self.electron_dxybs_original)

        if self.correct_muon:
            corr = self.cset[self.muon_correction_name]
            self.muon_dxybs = {
                var: _evaluate_jagged(corr, events.Muon.dxybs, var)
                for var in ("nom", "up", "down")
            }
        else:
            self.muon_dxybs = dict.fromkeys(("nom", "up", "down"), self.muon_dxybs_original)

    def calibrate(self, events, orig_colls, variation, already_applied_calibrators=None):
        electron_dxybs = self.electron_dxybs["nom"]
        if variation == "electron_d0_correctionUp":
            electron_dxybs = self.electron_dxybs["up"]
        elif variation == "electron_d0_correctionDown":
            electron_dxybs = self.electron_dxybs["down"]

        muon_dxybs = self.muon_dxybs["nom"]
        if variation == "muon_d0_correctionUp":
            muon_dxybs = self.muon_dxybs["up"]
        elif variation == "muon_d0_correctionDown":
            muon_dxybs = self.muon_dxybs["down"]

        return {
            "Electron.dxybs": electron_dxybs,
            "Electron.dxybs_original": self.electron_dxybs_original,
            "Muon.dxybs": muon_dxybs,
            "Muon.dxybs_original": self.muon_dxybs_original,
        }
