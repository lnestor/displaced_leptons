import awkward as ak
import numpy as np
from coffea.processor import column_accumulator
from coffea.analysis_tools import PackedSelection
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
from object_selection import (
    build_progressive_electron_collections,
    build_progressive_muon_collections,
)

CENTRAL_NANOAOD_FLAG = 0

# Maps each stage label to the (ele_coll, mu_coll) to use for saved kinematics.
# None means that lepton type has not been selected yet at that stage.
_STAGE_COLLS = {
    "Stage00_Trigger":   ("Electron",       "Muon"),
    "Stage02_EleEta":    ("ElectronEta",    None),
    "Stage03_EleSC":     ("ElectronSC",     None),
    "Stage04_EleEtaPhi": ("ElectronEtaPhi", None),
    "Stage05_ElePt":     ("ElectronPt",     None),
    "Stage06_EleID":     ("ElectronID",     None),
    "Stage07_EleIso":    ("ElectronGood",   None),
    "Stage08_MuEta":     ("ElectronGood",   "MuonEta"),
    "Stage09_MuEtaPhi":  ("ElectronGood",   "MuonEtaPhi"),
    "Stage10_MuPt":      ("ElectronGood",   "MuonPt"),
    "Stage11_MuGlobal":  ("ElectronGood",   "MuonGlobal"),
    "Stage12_MuID":      ("ElectronGood",   "MuonID"),
    "Stage13_MuIso":     ("ElectronGood",   "MuonGood"),
    "Stage14_CosAlpha":  ("ElectronGood",   "MuonGood"),
    "Stage15_DeltaT":    ("ElectronGood",   "MuonGood"),
    "Stage16_DeltaR":    ("ElectronGood",   "MuonGood"),
    "Stage17_NoDispVtx": ("ElectronGood",   "MuonGood"),
}

_STAGE_FIELDS = {
    "run":     np.uint32,
    "lumi":    np.uint32,
    "event":   np.uint64,
    "ele_pt":  np.float32,
    "ele_eta": np.float32,
    "mu_pt":   np.float32,
    "mu_eta":  np.float32,
}


def _empty_stage_acc():
    return {f: column_accumulator(np.array([], dtype=dt)) for f, dt in _STAGE_FIELDS.items()}


class DisplacedLeptonProcessor(BaseProcessorABC):

    def __init__(self, cfg):
        super().__init__(cfg)

        presel_labels = [getattr(cut, "label", cut.name) for cut in self._preselections]
        self.output_format["cutflow_cumulative"] = {
            "initial": {},
            "skim": {},
            "preselection": {},
            **{cat: {} for cat in self._categories}
        }
        self.output_format["stage_events"] = {
            "Stage00_Trigger": _empty_stage_acc(),
            **{label: _empty_stage_acc() for label in presel_labels},
        }

    # ------------------------------------------------------------------
    # Object preselection: builds all progressive collections
    # ------------------------------------------------------------------

    def apply_object_preselection(self, variation):
        ele = self.events.Electron
        mu = self.events.Muon

        if self._custom_nano_version != CENTRAL_NANOAOD_FLAG:
            if self._year in ["2016_PreVFP", "2016_PostVFP", "2017", "2018"]:
                rho = self.events.fixedGridRhoFastjetAll
            else:
                rho = self.events.Rho.fixedGridRhoFastjetAll

            ele_iso = np.maximum(
                ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt + ele.pfIso03_sumNeutral
                - rho * np.pi * 0.3**2,
                0,
            ) / ele.pt
            self.events["Electron"] = ak.with_field(self.events.Electron, ele_iso, "customIso")
            self.events["Electron"] = ak.with_field(
                self.events.Electron, abs(self.events.Electron.dxybs) * 1e4, "absd0_um"
            )

            mu_iso = np.maximum(
                mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutral
                - rho * np.pi * 0.4**2,
                0,
            ) / mu.pt
            self.events["Muon"] = ak.with_field(self.events.Muon, mu_iso, "customIso")
            self.events["Muon"] = ak.with_field(
                self.events.Muon, abs(self.events.Muon.dxybs) * 1e4, "absd0_um"
            )
        else:
            self.events["Electron"] = ak.with_field(self.events.Electron, ele.pfRelIso03_all, "customIso")
            self.events["Electron"] = ak.with_field(
                self.events.Electron, abs(ele.dxy) * 1e4, "absd0_um"
            )
            self.events["Muon"] = ak.with_field(self.events.Muon, mu.pfRelIso04_all, "customIso")
            self.events["Muon"] = ak.with_field(
                self.events.Muon, abs(mu.dxybs) * 1e4, "absd0_um"
            )
            self.events["Muon"] = ak.with_field(
                self.events.Muon, ak.zeros_like(mu.pt), "timeAtIpInOut"
            )
            self.events["Muon"] = ak.with_field(
                self.events.Muon, ak.zeros_like(mu.pt), "timeNdof"
            )
            n = len(self.events)
            self.events["InMaterialVtx"] = ak.zip({
                "lep1Idx":    ak.Array([[]] * n),
                "lep2Idx":    ak.Array([[]] * n),
                "lep1Flavor": ak.Array([[]] * n),
                "lep2Flavor": ak.Array([[]] * n),
            })

        for name, coll in build_progressive_electron_collections(
            self.events, self._year, self.params
        ).items():
            self.events[name] = coll

        for name, coll in build_progressive_muon_collections(
            self.events, self._year, self.params
        ).items():
            self.events[name] = coll

    def count_objects(self, variation):
        self.events["nElectronGood"] = ak.num(self.events.ElectronGood)
        self.events["nMuonGood"] = ak.num(self.events.MuonGood)
        self.events["nLeptonGood"] = self.events["nElectronGood"] + self.events["nMuonGood"]

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def load_metadata_extra(self):
        with uproot.open(self.events.metadata["filename"]) as f:
            if "customNanoVersion" in f:
                self._custom_nano_version = int(f["customNanoVersion"])
            else:
                self._custom_nano_version = CENTRAL_NANOAOD_FLAG

    # ------------------------------------------------------------------
    # Stage-event output helpers
    # ------------------------------------------------------------------

    def _save_stage_events(self, events, label, ele_coll, mu_coll):
        """Write (run, lumi, event, leading lepton kinematics) for one stage."""
        n = len(events)

        if ele_coll is not None:
            leading_ele = ak.pad_none(events[ele_coll], 1)[:, 0]
            ele_pt  = ak.to_numpy(ak.fill_none(leading_ele.pt,  -1.0)).astype(np.float32)
            ele_eta = ak.to_numpy(ak.fill_none(leading_ele.eta, -99.0)).astype(np.float32)
        else:
            ele_pt  = np.full(n, -1.0,  dtype=np.float32)
            ele_eta = np.full(n, -99.0, dtype=np.float32)

        if mu_coll is not None:
            leading_mu = ak.pad_none(events[mu_coll], 1)[:, 0]
            mu_pt  = ak.to_numpy(ak.fill_none(leading_mu.pt,  -1.0)).astype(np.float32)
            mu_eta = ak.to_numpy(ak.fill_none(leading_mu.eta, -99.0)).astype(np.float32)
        else:
            mu_pt  = np.full(n, -1.0,  dtype=np.float32)
            mu_eta = np.full(n, -99.0, dtype=np.float32)

        self.output["stage_events"][label] = {
            "run":     column_accumulator(ak.to_numpy(events.run).astype(np.uint32)),
            "lumi":    column_accumulator(ak.to_numpy(events.luminosityBlock).astype(np.uint32)),
            "event":   column_accumulator(ak.to_numpy(events.event).astype(np.uint64)),
            "ele_pt":  column_accumulator(ele_pt),
            "ele_eta": column_accumulator(ele_eta),
            "mu_pt":   column_accumulator(mu_pt),
            "mu_eta":  column_accumulator(mu_eta),
        }

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def process_extra_after_skim(self):
        # Cumulative skim cutflow counts
        self.output["cutflow_cumulative"]["initial"][self._dataset] = self.nEvents_initial
        names = list(self._skim_masks.names)
        for i, cut_name in enumerate(names):
            cumul = ak.sum(self._skim_masks.all(*names[:i + 1]))
            short_name = cut_name.split("__")[0]
            self.output["cutflow_cumulative"]["skim"].setdefault(short_name, {})[self._dataset] = cumul

        # Stage00 event data (object preselection has not run yet; use raw collections)
        ele_coll, mu_coll = _STAGE_COLLS["Stage00_Trigger"]
        self._save_stage_events(self.events, "Stage00_Trigger", ele_coll, mu_coll)

    def process_extra_before_presel(self, variation):
        # Snapshot the post-skim, pre-preselection event array so we can index
        # back into it per stage inside process_extra_after_presel.
        if variation == "nominal":
            self._events_before_presel = self.events

    def process_extra_after_presel(self, variation):
        if variation != "nominal":
            return

        # Cumulative preselection cutflow counts
        names = list(self._presel_masks.names)
        for i, cut_name in enumerate(names):
            cumul = ak.sum(self._presel_masks.all(*names[:i + 1]))
            short_name = cut_name.split("__")[0]
            self.output["cutflow_cumulative"]["preselection"] \
                .setdefault(short_name, {}) \
                .setdefault(self._dataset, {})["nominal"] = cumul

        # Per-stage event data
        for i, cut in enumerate(self._preselections):
            label = getattr(cut, "label", cut.name)
            cumul_mask = self._presel_masks.all(*names[:i + 1])
            evts = self._events_before_presel[cumul_mask]
            ele_coll, mu_coll = _STAGE_COLLS.get(label, ("ElectronGood", "MuonGood"))
            self._save_stage_events(evts, label, ele_coll, mu_coll)

    # ------------------------------------------------------------------
    # Preselection mask (keeps _presel_masks for later use)
    # ------------------------------------------------------------------

    def get_preselection_mask(self, variation):
        self._presel_masks = PackedSelection()
        for cut in self._preselections:
            mask = cut.get_mask(
                self.events,
                processor_params=self.params,
                year=self._year,
                sample=self._sample,
                isMC=self._isMC,
            )
            self._presel_masks.add(cut.id, mask)
        return self._presel_masks.all(*self._presel_masks.names)

    # ------------------------------------------------------------------
    # Postprocess
    # ------------------------------------------------------------------

    def postprocess(self, accumulator):
        accumulator = super().postprocess(accumulator)
        accumulator["cut_labels"] = {
            "skim": [getattr(cut, "label", cut.name) for cut in self.cfg.skim],
            "preselection": [getattr(cut, "label", cut.name) for cut in self.cfg.preselections],
            **{
                category: [getattr(cut, "label", cut.name) for cut in cuts]
                for category, cuts in self.cfg.categories_cfg.items()
            },
        }

        for stage in accumulator["cut_labels"].keys():
            accumulator["cut_labels"][stage] = [
                label for label in accumulator["cut_labels"][stage]
                if label != "passthrough"
            ]
            if "passthrough" in accumulator["cutflow_cumulative"].get(stage, {}):
                del accumulator["cutflow_cumulative"][stage]["passthrough"]

        return accumulator
