import awkward as ak
from pocket_coffea.workflows.base import BaseProcessorABC
from object_selection import displaced_lepton_selection

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)

    def apply_object_preselection(self, variation):
        self.events["ElectronGood"] = displaced_lepton_selection(self.events, "Electron", self._year, self.params)
        self.events["MuonGood"] = displaced_lepton_selection(self.events, "Muon", self._year, self.params)
        self.events["ElectronGood"] = ak.with_field(self.events.ElectronGood, abs(self.events.ElectronGood.dxy) * 1e4, "absd0_um")
        self.events["MuonGood"] = ak.with_field(self.events.MuonGood, abs(self.events.MuonGood.dxy) * 1e4, "absd0_um")

    def count_objects(self, variation):
        self.events["nElectronGood"] = ak.num(self.events.ElectronGood)
        self.events["nMuonGood"] = ak.num(self.events.MuonGood)
        self.events["nLeptonGood"] = (self.events["nElectronGood"] + self.events["nMuonGood"])
