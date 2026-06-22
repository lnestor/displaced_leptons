import awkward as ak
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
from object_selection import displaced_lepton_selection
import numpy as np

CENTRAL_NANOAOD_FLAG = 0

RUN_2_YEARS = ['2016_PreVFP', '2016_PostVFP', '2017', '2018']

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)

    def apply_object_preselection(self, variation):
        ele = self.events.Electron
        mu = self.events.Muon

        self.events["Muon", "customIsoCorr"] = rho * np.pi * 0.4**2

        if self._custom_nano_version != CENTRAL_NANOAOD_FLAG:
            if self._year in RUN_2_YEARS:
                rho = self.events.fixedGridRhoFastjetAll
            else:
                rho = self.events.Rho.fixedGridRhoFastjetAll

            ele_iso = np.maximum(ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt + ele.pfIso03_sumNeutral - rho * np.pi * 0.3**2, 0) / ele.pt
            self.events["Electron", "customIso"] = ele_iso
            self.events["Electron", "absd0_um"] = abs(self.events.Electron.dxybs) * 1e4

            mu_iso = np.maximum(mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutral - rho * np.pi * 0.4**2, 0) / mu.pt
            self.events["Muon", "customIso"] = mu_iso
            self.events["Muon", "absd0_um"] = abs(self.events.Muon.dxybs) * 1e4
            self.events["Muon", "standardIsoCorr"] = mu.pfIso04_sumPUPt / 2
        else:
            self.events["Electron", "customIso"] = ele.pfRelIso03_all
            self.events["Electron", "absd0_um"] = abs(ele.dxy) * 1e4

            self.events["Muon", "customIso"] = mu.pfRelIso04_all
            self.events["Muon", "absd0_um"] = abs(mu.dxybs) * 1e4
            self.events["Muon", "timeAtIpInOut"] = ak.zeros_like(mu.pt)
            self.events["Muon", "timeNdof"] = ak.zeros_like(mu.pt)
            self.events["Muon", "standardIsoCorr"] = ak.zeros_like(mu.pt)

            n = len(self.events)
            self.events["InMaterialVtx"] = ak.zip({
                "lep1Idx": ak.Array([[]]*n),
                "lep2Idx": ak.Array([[]]*n),
                "lep1Flavor": ak.Array([[]]*n),
                "lep2Flavor": ak.Array([[]]*n)
            })

        self.events["ElectronGood"] = displaced_lepton_selection(self.events, "Electron", self._year, self.params)
        self.events["MuonGood"] = displaced_lepton_selection(self.events, "Muon", self._year, self.params)


    def count_objects(self, variation):
        self.events["nElectronGood"] = ak.num(self.events.ElectronGood)
        self.events["nMuonGood"] = ak.num(self.events.MuonGood)
        self.events["nLeptonGood"] = (self.events["nElectronGood"] + self.events["nMuonGood"])


    def load_metadata_extra(self):
        with uproot.open(self.events.metadata["filename"]) as f:
            if "customNanoVersion" in f:
                self._custom_nano_version = int(f["customNanoVersion"])
            else:
                self._custom_nano_version = CENTRAL_NANOAOD_FLAG
