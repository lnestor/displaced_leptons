import awkward as ak
from coffea.analysis_tools import PackedSelection
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
from object_selection import displaced_lepton_selection
import numpy as np

CENTRAL_NANOAOD_FLAG = 0

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.output_format["cutflow_cumulative"] = {
            "initial": {},
            "skim": {},
            "preselection": {},
            **{cat: {} for cat in self._categories}
        }


    def apply_object_preselection(self, variation):
        ele = self.events.Electron
        mu = self.events.Muon

        if self._custom_nano_version != CENTRAL_NANOAOD_FLAG:
            if self._year in ['2016_PreVFP', '2016_PostVFP', '2017', '2018']:
                rho = self.events.fixedGridRhoFastjetAll
            else:
                rho = self.events.Rho.fixedGridRhoFastjetAll

            ele_iso = np.maximum(ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt + ele.pfIso03_sumNeutral - rho * np.pi * 0.3**2, 0) / ele.pt
            self.events["Electron"] = ak.with_field(self.events.Electron, ele_iso, "customIso")
            self.events["Electron"] = ak.with_field(self.events.Electron, abs(self.events.Electron.dxybs) * 1e4, "absd0_um")

            mu_iso = np.maximum(mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutral - rho * np.pi * 0.4**2, 0) / mu.pt
            self.events["Muon"] = ak.with_field(self.events.Muon, mu_iso, "customIso")
            self.events["Muon"] = ak.with_field(self.events.Muon, abs(self.events.Muon.dxybs) * 1e4, "absd0_um")
        else:
            self.events["Electron"] = ak.with_field(self.events.Electron, ele.pfRelIso03_all, "customIso")
            self.events["Electron"] = ak.with_field(self.events.Electron, abs(ele.dxy) * 1e4, "absd0_um")

            self.events["Muon"] = ak.with_field(self.events.Muon, mu.pfRelIso04_all, "customIso")
            self.events["Muon"] = ak.with_field(self.events.Muon, abs(mu.dxybs) * 1e4, "absd0_um")
            self.events["Muon"] = ak.with_field(self.events.Muon, ak.zeros_like(mu.pt), "timeAtIpInOut")
            self.events["Muon"] = ak.with_field(self.events.Muon, ak.zeros_like(mu.pt), "timeNdof")

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


    def process_extra_after_skim(self):
        self.output["cutflow_cumulative"]["initial"][self._dataset] = self.nEvents_initial
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
            **{
                category: [getattr(cut, "label", cut.name) for cut in cuts]
                for category, cuts in self.cfg.categories_cfg.items()
            }
        }
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

