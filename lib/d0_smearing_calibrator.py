import numpy as np
import awkward as ak

from pocket_coffea.lib.calibrators.calibrator import Calibrator
from pocket_coffea.utils.utils import get_random_seed


def _smear_jagged(values, width, rng):
    flat_smear = rng.normal(loc=0.0, scale=width, size=len(ak.flatten(values)))
    return ak.unflatten(flat_smear, ak.num(values))


# TODO: I think this fails when we don't have supplements because the supplement schema is never applied
# in that case. Unsure if this is worth handling or not.


class D0SmearingCalibrator(Calibrator):
    name = "d0_smearing_calibrator"
    has_variations = True
    isMC_only = True
    calibrated_collections = ["Electron.dxybs", "Electron.dxybs_original", "Muon.dxybs", "Muon.dxybs_original"]

    def __init__(self, params, metadata, do_variations, **kwargs):
        super().__init__(params, metadata, do_variations, **kwargs)
        self.smearing_params = self.params.d0_smearing[metadata["year"]]
        self.smear_electron = "Electron" in self.smearing_params
        self.smear_muon = "Muon" in self.smearing_params

        self._variations = []
        if self.smear_electron:
            self._variations += ["electron_d0_smearingUp", "electron_d0_smearingDown"]
        if self.smear_muon:
            self._variations += ["muon_d0_smearingUp", "muon_d0_smearingDown"]

    def initialize(self, events):
        seed = get_random_seed(events.metadata, salt="D0SmearingCalibrator")
        rng = np.random.default_rng(seed)

        self.electron_dxybs_original = events.Electron.dxybs
        self.muon_dxybs_original = events.Muon.dxybs

        if self.smear_electron:
            ele_sigma = self.smearing_params["Electron"]["sigma"]
            ele_err = self.smearing_params["Electron"]["error"]
            ele_smear = _smear_jagged(events.Electron.dxybs, ele_sigma, rng)
            self.electron_dxybs = {
                "nominal": events.Electron.dxybs + ele_smear,
                "up": events.Electron.dxybs + ele_smear * (ele_sigma + ele_err) / ele_sigma,
                "down": events.Electron.dxybs + ele_smear * (ele_sigma - ele_err) / ele_sigma,
            }
        else:
            self.electron_dxybs = {
                "nominal": self.electron_dxybs_original,
                "up": self.electron_dxybs_original,
                "down": self.electron_dxybs_original,
            }

        if self.smear_muon:
            mu_sigma = self.smearing_params["Muon"]["sigma"]
            mu_err = self.smearing_params["Muon"]["error"]
            mu_smear = _smear_jagged(events.Muon.dxybs, mu_sigma, rng)
            self.muon_dxybs = {
                "nominal": events.Muon.dxybs + mu_smear,
                "up": events.Muon.dxybs + mu_smear * (mu_sigma + mu_err) / mu_sigma,
                "down": events.Muon.dxybs + mu_smear * (mu_sigma - mu_err) / mu_sigma,
            }
        else:
            self.muon_dxybs = {
                "nominal": self.muon_dxybs_original,
                "up": self.muon_dxybs_original,
                "down": self.muon_dxybs_original,
            }

    def calibrate(self, events, orig_colls, variation, already_applied_calibrators=None):
        if variation == "electron_d0_smearingUp":
            electron_dxybs = self.electron_dxybs["up"]
        elif variation == "electron_d0_smearingDown":
            electron_dxybs = self.electron_dxybs["down"]
        else:
            electron_dxybs = self.electron_dxybs["nominal"]

        if variation == "muon_d0_smearingUp":
            muon_dxybs = self.muon_dxybs["up"]
        elif variation == "muon_d0_smearingDown":
            muon_dxybs = self.muon_dxybs["down"]
        else:
            muon_dxybs = self.muon_dxybs["nominal"]

        return {
            "Electron.dxybs": electron_dxybs,
            "Electron.dxybs_original": self.electron_dxybs_original,
            "Muon.dxybs": muon_dxybs,
            "Muon.dxybs_original": self.muon_dxybs_original,
        }
