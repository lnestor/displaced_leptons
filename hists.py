from pocket_coffea.parameters.histograms import HistConf, Axis

def lepton_hists(coll=None, label=None):
    return {
        f"{label}_pt": HistConf([Axis(coll=coll, field="pt", bins=200, start=0, stop=2000, label=rf"{label} $p_T$ [GeV]")]),
        f"{label}_eta": HistConf([Axis(coll=coll, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")]),
        f"{label}_d0_all": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ [$\mu m$]")]),
        f"{label}_d0_cr": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=50, label=rf"{label} $|d_0|$ [$\mu m$]")])
    }

def background_hists():
    abcd_pt_bins = [0, 90, 100, 140, 300, 400, 1e6] # 1e6 is just a really high number to simulate infinity
    abcd_d0_bins = [1, 1e1, 1e2, 5e2, 1e3, 5e3, 1e4, 5e4, 1e5]
    return {
        "abcd_ee": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="ElectronGood", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="ElectronGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Electron $p_T$"),
            ],
            only_categories=["ee"]
        ),
        "abcd_emu": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["emu"]
        ),
        "abcd_mumu": HistConf(
            [
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["mumu"]
        ),
        "d0d0_ee": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="ElectronGood", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Electron $|d_0|$ [$\mu m$]")
            ],
            only_categories=["ee"]
        ),
        "d0d0_emu": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=100, start=0, stop=200, label=rf"Leading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["emu"]
        ),
        "d0d0_mumu": HistConf(
            [
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["mumu"]
        )
    }

