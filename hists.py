from pocket_coffea.parameters.histograms import HistConf, Axis

def lepton_hists(coll=None, label=None):
    return {
        f"{label}_pt": HistConf([Axis(coll=coll, field="pt", bins=200, start=0, stop=2000, label=rf"{label} $p_T$ [GeV]")]),
        f"{label}_eta": HistConf([Axis(coll=coll, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")]),
        f"{label}_d0": HistConf([Axis(coll=coll, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ ($\mu m$)")]),
    }
