from pocket_coffea.parameters.histograms import HistConf, Axis

def lepton_hists(coll=None, label=None):
    return {
        f"{label}_pt": HistConf([Axis(coll=coll, field="pt", bins=200, start=0, stop=2000, label=rf"{label} $p_T$ [GeV]")]),
        f"{label}_eta": HistConf([Axis(coll=coll, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")]),
        f"{label}_d0_all": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ [$\mu m$]")]),
        f"{label}_d0_cr": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=50, label=rf"{label} $|d_0|$ [$\mu m$]")])
    }

def abcd_hists():
    pt_bins = [0, 90, 100, 140, 300, 400, 1e6] # 1e6 is just a really high number to simulate infinity
    return {
        "abcd_ee": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 500, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="ElectronGood", field="absd0_um", pos=1, bins=[0, 100, 500, 1e5], label=rf"Subleading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="ElectronGood", field="pt", pos=0, bins=pt_bins, label=rf"Leading Electron $p_T$"),
            ],
            only_categories=["ee"]
        ),
        "abcd_emu": HistConf(
            [
                Axis(coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 500, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=[0, 100, 500, 1e5], label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="pt", pos=0, bins=pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["emu"]
        ),
        "abcd_mumu": HistConf(
            [
                Axis(coll="MuonGood", field="absd0_um", pos=0, bins=[0, 100, 500, 1e5], label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="absd0_um", pos=1, bins=[0, 100, 500, 1e5], label=rf"Subleading Muon $|d_0|$ [$\mu m$]"),
                Axis(coll="MuonGood", field="pt", pos=0, bins=pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["mumu"]
        ),
    }
