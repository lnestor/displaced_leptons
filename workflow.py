import awkward as ak
from coffea.analysis_tools import PackedSelection
from pocket_coffea.workflows.base import BaseProcessorABC
import uproot
from lib.object_cutflow import ObjectCutflow
from object_selection import min_pt, max_eta, sc_gap_veto, lepton_id, isolation, eta_phi_veto, electron_tight_id
from lib.named_cut import NamedCut
import numpy as np

CENTRAL_NANOAOD_FLAG = 0

RUN_2_YEARS = ['2016_PreVFP', '2016_PostVFP', '2017', '2018']

class DisplacedLeptonProcessor(BaseProcessorABC):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.output_format["cutflow_cumulative"] = {
            "initial": {},
            "skim": {},
            "preselection": {},
            "object_selection": {},
            **{cat: {} for cat in self._categories}
        }


    def apply_object_preselection(self, variation):
        if self._isMC:
            gen = self.events.GenPart
            self.events["GenPart"] = ak.with_field(self.events.GenPart, self.get_unique_parent_pdgid(gen), "uniqueGenPartMotherIdx")

        if self._custom_nano_version == CENTRAL_NANOAOD_FLAG:
            n = len(self.events)
            self.events["InMaterialVtx"] = ak.zip({
                "lep1Idx": ak.Array([[]]*n),
                "lep2Idx": ak.Array([[]]*n),
                "lep1Flavor": ak.Array([[]]*n),
                "lep2Flavor": ak.Array([[]]*n)
            })

        ele_cut_vals = self.params.object_preselection["Electron"][self._year]
        mu_cut_vals = self.params.object_preselection["Muon"][self._year]

        if self._needs_electrons():
            self.events["Electron"] = self._build_electrons()

        if self._needs_muons():
            self.events["Muon"] = self._build_muons()


        if self._needs_ee():
            ee_cuts = self._get_ele_cuts(ele_cut_vals, count=2)

            ee_cutflow = ObjectCutflow(collection="Electron", cuts=ee_cuts)
            ee_cutflow.run(self.events, self.params)

            self.events["ElectronGood_ee"] = self.events.Electron[ee_cutflow.get_final_object_mask()]

            event_cumul = ak.ones_like(self.events.event, dtype=bool)
            self._fill_object_cutflow(ee_cutflow, event_cumul, variation, min_count=2)

        if self._needs_emu():
            emu_ele_cuts = self._get_ele_cuts(ele_cut_vals, count=1)
            emu_mu_cuts = self._get_mu_cuts(mu_cut_vals, count=1)

            emu_ele_cutflow = ObjectCutflow(collection="Electron", cuts=emu_ele_cuts)
            emu_ele_cutflow.run(self.events, self.params)

            emu_mu_cutflow = ObjectCutflow(collection="Muon", cuts=emu_mu_cuts)
            emu_mu_cutflow.run(self.events, self.params)

            self.events["ElectronGood_emu"] = self.events.Electron[emu_ele_cutflow.get_final_object_mask()]
            self.events["MuonGood_emu"] = self.events.Muon[emu_mu_cutflow.get_final_object_mask()]

            event_cumul = ak.ones_like(self.events.event, dtype=bool)
            event_cumul = self._fill_object_cutflow(emu_ele_cutflow, event_cumul, variation, min_count=1)
            self._fill_object_cutflow(emu_mu_cutflow, event_cumul, variation, min_count=1)

        if self._needs_mumu():
            mumu_cuts = self._get_mu_cuts(mu_cut_vals, count=2)

            mumu_cutflow = ObjectCutflow(collection="Muon", cuts=mumu_cuts)
            mumu_cutflow.run(self.events, self.params)

            self.events["MuonGood_mumu"] = self.events.Muon[mumu_cutflow.get_final_object_mask()]

            event_cumul = ak.ones_like(self.events.event, dtype=bool)
            self._fill_object_cutflow(mumu_cutflow, event_cumul, variation, min_count=2)


    def gen_match(self, coll, gen):
        dR = coll[:, :, np.newaxis].delta_r(gen[:, np.newaxis, :])
        min_dR = ak.min(dR, axis=2)
        best_idx = ak.fill_none(ak.argmin(dR, axis=2), 0)

        matched = ak.fill_none(min_dR < 0.1, False)
        gen_padded = ak.pad_none(gen, 1, axis=1)
        return ak.mask(gen_padded[best_idx], matched)


    def get_unique_parent_pdgid(self, gen):
        current_idx = gen.genPartIdxMother
        start_pdgid = abs(gen.pdgId)

        while True:
            no_mother = current_idx < 0
            safe_idx = ak.where(no_mother, 0, current_idx)
            same_pdgid = abs(gen[safe_idx].pdgId) == start_pdgid
            still_searching = ~no_mother & same_pdgid

            if not ak.any(still_searching):
                break

            next_idx = gen[safe_idx].genPartIdxMother
            current_idx = ak.where(still_searching, next_idx, current_idx)

        safe_idx = ak.where(current_idx < 0, 0, current_idx)
        return ak.where(current_idx < 0, 0, abs(gen[safe_idx].pdgId))


    def count_objects(self, variation):
        pass


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
            "object_selection": list(accumulator["cutflow_cumulative"]["object_selection"].keys()),
            **{
                category: [getattr(cut, "label", cut.name) for cut in cuts]
                for category, cuts in self.cfg.categories_cfg.items()
            }
        }

        for stage in accumulator["cut_labels"].keys():
            accumulator["cut_labels"][stage] = [
                label for label in accumulator["cut_labels"][stage]
                if label != "passthrough"
            ]

            if "passthrough" in accumulator["cutflow_cumulative"][stage]:
                del accumulator["cutflow_cumulative"][stage]["passthrough"]

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

    def _build_electrons(self):
        self.events["Electron", "original_idx"] = ak.local_index(self.events.Electron, axis=1)

        if self._year in RUN_2_YEARS:
            rho = self.events.fixedGridRhoFastjetAll
        else:
            rho = self.events.Rho.fixedGridRhoFastjetAll

        ele = self.events.Electron
        gen = self.events.GenPart

        if self._isMC:
            gen_ele = gen[(abs(gen.pdgId) == 11) & (gen.status == 1) & (gen.pt > 10)]
            matched_ele = self.gen_match(ele, gen_ele)
            self.events["Electron"] = ak.with_field(self.events.Electron, ak.fill_none(matched_ele.uniqueGenPartMotherIdx, 0), "uniqueGenPartMotherIdx")

        if self._custom_nano_version != CENTRAL_NANOAOD_FLAG:
            ele_iso = np.maximum(ele.pfIso03_sumChargedHadronPt + ele.pfIso03_sumPUPt + ele.pfIso03_sumNeutral - rho * np.pi * 0.3**2, 0) / ele.pt
            self.events["Electron", "customIso"] = ele_iso
            self.events["Electron", "absd0_um"] = abs(self.events.Electron.dxybs) * 1e4
            self.events["Electron", "is_gap"] = ele.isEBEEGap
        else:
            self.events["Electron", "customIso"] = ele.pfRelIso03_all
            self.events["Electron", "absd0_um"] = abs(ele.dxy) * 1e4

            eta_sc = abs(ele.deltaEtaSC + ele.eta)
            self.events["Electron", "is_gap"] = (eta_sc >= 1.442) & (eta_sc <= 1.566)

        return self.events.Electron

    def _build_muons(self):
        self.events["Muon", "original_idx"] = ak.local_index(self.events.Muon, axis=1)
        self.events["Muon", "absd0_um"] = abs(self.events.Muon.dxybs) * 1e4

        if self._year in RUN_2_YEARS:
            rho = self.events.fixedGridRhoFastjetAll
        else:
            rho = self.events.Rho.fixedGridRhoFastjetAll
        self.events["Muon", "customIsoCorr"] = rho * np.pi * 0.4**2

        mu = self.events.Muon
        gen = self.events.GenPart

        if self._isMC:
            gen_mu = gen[(abs(gen.pdgId) == 13) & (gen.status == 1) & (gen.pt > 10)]
            matched_mu = self.gen_match(mu, gen_mu)
            self.events["Muon"] = ak.with_field(self.events.Muon, ak.fill_none(matched_mu.uniqueGenPartMotherIdx, 0), "uniqueGenPartMotherIdx")

        if self._custom_nano_version != CENTRAL_NANOAOD_FLAG:
            mu_iso = np.maximum(mu.pfIso04_sumChargedHadronPt + mu.pfIso04_sumPUPt + mu.pfIso04_sumNeutral - rho * np.pi * 0.4**2, 0) / mu.pt
            self.events["Muon", "customIso"] = mu_iso
            self.events["Muon", "standardIsoCorr"] = mu.pfIso04_sumPUPt / 2
        else:
            self.events["Muon", "customIso"] = mu.pfRelIso04_all
            self.events["Muon", "timeAtIpInOut"] = ak.zeros_like(mu.pt)
            self.events["Muon", "timeNdof"] = ak.zeros_like(mu.pt)
            self.events["Muon", "standardIsoCorr"] = ak.zeros_like(mu.pt)

        return self.events.Muon

    def _get_ele_cuts(self, cut_vals, count=1):
        cuts = [
            NamedCut(min_pt("Electron", cut_vals.pt), label=f"$>={count}$ e with $p_T > {cut_vals.pt}$ GeV"),
            NamedCut(max_eta("Electron", cut_vals.eta), label=f"$>={count}$ e with $|\\eta| < {cut_vals.eta}$"),
            NamedCut(sc_gap_veto("Electron"), label=f"$>={count}$ e not in supercluster gap"),
            NamedCut(electron_tight_id(), label=f"$>={count}$ e passing tight ID"),
            NamedCut(isolation("Electron", cut_vals.iso_base, cut_vals.iso_pt_dep), label=f"$>={count}$ e passing tight custom isolation"),
        ]

        if self.cfg.workflow_options["skip_pt_cut"]:
            del cuts[0]

        if "etaphi_veto" in cut_vals.keys():
            v = cut_vals.etaphi_veto
            new_cut = NamedCut(eta_phi_veto("Electron", v.eta_min, v.eta_max, v.phi_min, v.phi_max), label=f"$>={count}$ e passing $\\eta$-$\\phi$ veto")
            cuts.insert(2, new_cut)

        return cuts

    def _get_mu_cuts(self, cut_vals, count=1):
        cuts = [
            NamedCut(min_pt("Muon", cut_vals.pt), label=f"$>={count}$ $\\mu$ with $p_T > {cut_vals.pt}$ GeV"),
            NamedCut(max_eta("Muon", cut_vals.eta), label=f"$>={count}$ $\\mu$ with $|\\eta| < {cut_vals.eta}$"),
            NamedCut(lepton_id("Muon", cut_vals.id, True), label=f"$>={count}$ $\\mu$ passing tight ID"),
            NamedCut(isolation("Muon", cut_vals.iso_base, cut_vals.iso_pt_dep), label=f"$>={count}$ $\\mu$ passing tight custom isolation"),
        ]

        if self.cfg.workflow_options["skip_pt_cut"]:
            del cuts[0]

        if "etaphi_veto" in cut_vals.keys():
            v = cut_vals.etaphi_veto
            new_cut = NamedCut(eta_phi_veto("Muon", v.eta_min, v.eta_max, v.phi_min, v.phi_max), label=f"$>={count}$ $\\mu$ passing $\\eta$-$\\phi$ veto")
            cuts.insert(2, new_cut)

        return cuts

    def _fill_object_cutflow(self, cutflow, event_cumul, variation, min_count=1):
        obj_sel = self.output["cutflow_cumulative"]["object_selection"]

        for i in range(len(cutflow)):
            event_cumul = event_cumul & cutflow.get_event_mask(i, min_count=min_count)
            count = int(ak.sum(event_cumul))
            obj_sel.setdefault(cutflow.cuts[i].label, {}).setdefault(self._dataset, {})[variation] = count

        return event_cumul


    def _needs_electrons(self):
        return self._needs_ee() or self._needs_emu()


    def _needs_muons(self):
        return self._needs_emu() or self._needs_mumu()


    def _needs_ee(self):
        return self._sample == "EGamma" or self._isMC or self._sample == "MET"


    def _needs_emu(self):
        return self._sample == "MuonEG" or self._isMC or self._sample == "MET"


    def _needs_mumu(self):
        return self._sample == "Muon" or self._isMC or self._sample == "MET"
