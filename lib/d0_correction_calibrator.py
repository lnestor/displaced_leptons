import numpy as np
import awkward as ak
from scipy.stats import norm

from pocket_coffea.lib.calibrators.calibrator import Calibrator

# Fits are done on the absd0_um histogram (micrometers); dxybs is in cm.
UM_TO_CM = 1e-4


def _mixture_cdf(x, mu, q, s1, s2):
    return q * norm.cdf(x, mu, s1) + (1 - q) * norm.cdf(x, mu, s2)


def _quantile_remap(x, fit_from, fit_to, fit_range, n_grid=4000, pad_factor=3.0):
    """Maps x from fit_from's double-Gaussian distribution to fit_to's, by
    matching CDF quantiles: x_new = F_to^-1(F_from(x))."""
    pad = pad_factor * max(fit_from["sigma2"], fit_to["sigma2"])
    x_grid = np.linspace(fit_range[0] - pad, fit_range[1] + pad, n_grid)
    cdf_to_grid = _mixture_cdf(x_grid, fit_to["mean"], fit_to["q"], fit_to["sigma1"], fit_to["sigma2"])

    u = _mixture_cdf(x, fit_from["mean"], fit_from["q"], fit_from["sigma1"], fit_from["sigma2"])
    return np.interp(u, cdf_to_grid, x_grid)


def _scale_fit(fit, factor):
    return {
        "mean": fit["mean"] * factor,
        "q": fit["q"],
        "sigma1": fit["sigma1"] * factor,
        "sigma2": fit["sigma2"] * factor,
    }


def _correct_jagged(values, fit_mc, fit_data, fit_range):
    flat = ak.to_numpy(ak.flatten(values))
    flat_corrected = _quantile_remap(flat, fit_mc, fit_data, fit_range)
    return ak.unflatten(flat_corrected, ak.num(values))


class D0CorrectionCalibrator(Calibrator):
    name = "d0_correction_calibrator"
    has_variations = False
    isMC_only = True
    calibrated_collections = ["Electron.dxybs", "Electron.dxybs_original", "Muon.dxybs", "Muon.dxybs_original"]

    def __init__(self, params, metadata, do_variations, **kwargs):
        super().__init__(params, metadata, do_variations, **kwargs)
        self.correction_params = self.params.d0_correction[metadata["year"]]
        self.correct_electron = "Electron" in self.correction_params
        self.correct_muon = "Muon" in self.correction_params
        self._variations = []

    def initialize(self, events):
        self.electron_dxybs_original = events.Electron.dxybs
        self.muon_dxybs_original = events.Muon.dxybs

        if self.correct_electron:
            p = self.correction_params["Electron"]
            fit_mc = _scale_fit(p["mc"], UM_TO_CM)
            fit_data = _scale_fit(p["data"], UM_TO_CM)
            fit_range = tuple(v * UM_TO_CM for v in p["fit_range"])
            self.electron_dxybs = _correct_jagged(events.Electron.dxybs, fit_mc, fit_data, fit_range)
        else:
            self.electron_dxybs = self.electron_dxybs_original

        if self.correct_muon:
            p = self.correction_params["Muon"]
            fit_mc = _scale_fit(p["mc"], UM_TO_CM)
            fit_data = _scale_fit(p["data"], UM_TO_CM)
            fit_range = tuple(v * UM_TO_CM for v in p["fit_range"])
            self.muon_dxybs = _correct_jagged(events.Muon.dxybs, fit_mc, fit_data, fit_range)
        else:
            self.muon_dxybs = self.muon_dxybs_original

    def calibrate(self, events, orig_colls, variation, already_applied_calibrators=None):
        return {
            "Electron.dxybs": self.electron_dxybs,
            "Electron.dxybs_original": self.electron_dxybs_original,
            "Muon.dxybs": self.muon_dxybs,
            "Muon.dxybs_original": self.muon_dxybs_original,
        }
