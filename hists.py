from pocket_coffea.parameters.histograms import HistConf, Axis

def lepton_hists(coll=None, label=None, key=None, only_categories=None):
    key = key or label
    kwargs = {"only_categories": only_categories} if only_categories is not None else {}
    return {
        f"{key}_pt": HistConf([Axis(coll=coll, field="pt", bins=200, start=0, stop=2000, label=rf"{label} $p_T$ [GeV]")], **kwargs),
        f"{key}_eta": HistConf([Axis(coll=coll, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")], **kwargs),
        f"{key}_d0_all": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ [$\mu m$]")], **kwargs),
        f"{key}_d0_cr": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=50, label=rf"{label} $|d_0|$ [$\mu m$]")], **kwargs)
    }

def background_hists():
    abcd_pt_bins = [0, 90, 100, 140, 300, 400, 1e6]
    abcd_d0_bins = [1, 1e1, 1e2, 5e2, 1e3, 5e3, 1e4, 5e4, 1e5]
    return {
        "abcd_ee": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood_ee", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e2_d0", coll="ElectronGood_ee", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e1_pt", coll="ElectronGood_ee", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Electron $p_T$"),
            ],
            only_categories=["ee"]
        ),
        "abcd_emu": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood_emu", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_d0", coll="MuonGood_emu", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_pt", coll="MuonGood_emu", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["emu"]
        ),
        "abcd_mumu": HistConf(
            [
                Axis(name="mu1_d0", coll="MuonGood_mumu", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu2_d0", coll="MuonGood_mumu", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_pt", coll="MuonGood_mumu", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["mumu"]
        ),
        "d0d0_ee": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood_ee", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e2_d0", coll="ElectronGood_ee", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Electron $|d_0|$ [$\mu m$]")
            ],
            only_categories=["ee"]
        ),
        "d0d0_emu": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood_emu", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_d0", coll="MuonGood_emu", field="absd0_um", pos=0, bins=100, start=0, stop=200, label=rf"Leading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["emu"]
        ),
        "d0d0_mumu": HistConf(
            [
                Axis(name="mu1_d0", coll="MuonGood_mumu", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu2_d0", coll="MuonGood_mumu", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["mumu"]
        )
    }
