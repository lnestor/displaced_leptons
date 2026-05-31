import awkward as ak
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
from object_selection import displaced_lepton_selection

CENTRAL_NANOAOD_FLAG = 0

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)

    def apply_object_preselection(self, variation):
        self.events["ElectronGood"] = displaced_lepton_selection(self.events, "Electron", self._year, self.params)
        self.events["MuonGood"] = displaced_lepton_selection(self.events, "Muon", self._year, self.params)

        self.events["ElectronGood"] = ak.with_field(self.events.ElectronGood, abs(self.events.ElectronGood.dxy) * 1e4, "absd0_um")
        self.events["MuonGood"] = ak.with_field(self.events.MuonGood, abs(self.events.MuonGood.dxybs) * 1e4, "absd0_um")

        if self._custom_nano_version == 0:
            self.events["MuonGood"] = ak.with_field(self.events.MuonGood, ak.zeros_like(self.events.MuonGood.pt), "timeAtIpInOut")
            self.events["MuonGood"] = ak.with_field(self.events.MuonGood, ak.zeros_like(self.events.MuonGood.pt), "timeNdof")

            n = len(self.events)
            self.events["InMaterialVtx"] = ak.zip({
                "lep1Idx": ak.Array([[]]*n),
                "lep2Idx": ak.Array([[]]*n),
                "lep1Flavor": ak.Array([[]]*n),
                "lep2Flavor": ak.Array([[]]*n)
            })


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
