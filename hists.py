from pocket_coffea.parameters.histograms import HistConf, Axis

from configs.common import MC_SAMPLES


def lepton_hists(coll=None, label=None, pos=None, only_categories=None):
    return {
        f"{label}_pt": HistConf([Axis(coll=coll, pos=pos, field="pt", bins=200, start=0, stop=2000, label=rf"{label} $p_T$ [GeV]")], only_categories=only_categories),
        f"{label}_eta": HistConf([Axis(coll=coll, pos=pos, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")], only_categories=only_categories),
        f"{label}_absd0": HistConf([Axis(coll=coll, pos=pos, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ [$\mu m$]")], only_categories=only_categories),
        f"{label}_sabsd0": HistConf([Axis(coll=coll, pos=pos, field="sabsd0", bins=100, start=0, stop=10, label=rf"{label} $|d_0/\sigma_{{d_0}}|$")], only_categories=only_categories),
        f"{label}_d0": HistConf([Axis(coll=coll, pos=pos, field="d0_um", bins=100, start=-50, stop=50, label=rf"{label} $d_0$ [$\mu m$]")], only_categories=only_categories),
        f"{label}_d0vsphi": HistConf([
            Axis(coll=coll, pos=pos, field="phi", bins=100, start=-3.14, stop=3.14, label=rf"{label} $\phi$"),
            Axis(coll=coll, pos=pos, field="d0_um", bins=100, start=-20, stop=20, label=rf"{label} $d_0$ [$\mu m$]")
        ], only_categories=only_categories),
        f"{label}_ip3d": HistConf([Axis(coll=coll, pos=pos, field="ip3d_um", bins=100, start=0, stop=300, label=rf"{label} ip3d [$\mu m$]")], only_categories=only_categories),
        f"{label}_sip3d": HistConf([Axis(coll=coll, pos=pos, field="sip3d", bins=100, start=0, stop=10, label=rf"{label} sip3d")], only_categories=only_categories),
        # f"{label}_gen_absd0": HistConf([Axis(coll=coll, pos=pos, field="gen_absd0_um", bins=100, start=0, stop=500, label=rf"{label} truth $|d_0|$ [$\mu m$]")], only_categories=only_categories),
        # f"{label}_gen_absd0_vs_reco_absd0": HistConf([
            # Axis(coll=coll, pos=pos, field="gen_absd0_um", bins=100, start=0, stop=500, label=rf"{label} truth $|d_0|$ [$\mu m$]"),
            # Axis(coll=coll, pos=pos, field="absd0_um", bins=100, start=0, stop=500, label=rf"{label} reco $|d_0|$ [$\mu m$]"),
        # ], only_categories=only_categories),
    }


def beamspot_hists():
    return {
        "Beamspot_d0": HistConf([Axis(coll="Beamspot", field="d0", bins=50, start=0, stop=200, label="Beamspot $d_0$ [$\mu m$]")])
    }


def pcr_hists(coll=None, label=None, pos=None, only_categories=None, threshold=50):
    return {
        f"{label}_pt": HistConf([Axis(coll=coll, pos=pos, field="pt", bins=100, start=0, stop=500, label=rf"{label} $p_T$ [GeV]")], only_categories=only_categories),
        f"{label}_eta": HistConf([Axis(coll=coll, pos=pos, field="eta", bins=30, start=-1.5, stop=1.5, label=rf"{label} $\eta$")], only_categories=only_categories),
        f"{label}_absd0": HistConf([Axis(coll=coll, pos=pos, field="absd0_um", bins=threshold, start=0, stop=threshold, label=rf"{label} $|d_0|$ [$\mu m$]")], only_categories=only_categories),
        f"{label}_absd0_uncorrected": HistConf([Axis(coll=coll, pos=pos, field="absd0_um_original", bins=threshold, start=0, stop=threshold, label=rf"{label} uncorrected $|d_0|$ [$\mu m$]")], only_categories=only_categories),
        f"{label}_d0vsphi": HistConf([
            Axis(coll=coll, pos=pos, field="phi", bins=100, start=-3.14, stop=3.14, label=rf"{label} $\phi$"),
            Axis(coll=coll, pos=pos, field="d0_um", bins=100, start=-20, stop=20, label=rf"{label} $d_0$ [$\mu m$]")
        ], only_categories=only_categories),
    }


def _hist(coll, field, bins, start, stop, label, pos=None, cats=None, samples=None):
    return HistConf(
        [Axis(coll=coll, pos=pos, field=field, bins=bins, start=start, stop=stop, label=label)],
        only_categories=cats,
        only_samples=samples
    )


def _get_legs_from_channel(channel):
    if channel == "ee":
        return ("ElectronGood", 0, "Leading Electron"), ("ElectronGood", 1, "Subleading Electron")
    elif channel == "mumu":
        return ("MuonGood", 0, "Leading Muon"), ("MuonGood", 1, "Subleading Muon")
    elif channel == "emu":
        return ("ElectronGood", 0, "Electron"), ("MuonGood", 0, "Muon")
    else:
        raise ValueError(f"Channel {channel} is not valid.")


def genvtx_hists(only_categories=None):
    return {
        "genvtx_v0": _hist(coll="GenVtx", field="v0_um", bins=100, start=0, stop=1e5, label=r"GenVtx $v_0$ [$\mu m$]", cats=only_categories, samples=MC_SAMPLES),
        "genvtx_x_vs_y": HistConf([
            Axis(coll="GenVtx", field="x", bins=100, start=-0.02, stop=0.02, label=r"GenVtx $x$ [cm]"),
            Axis(coll="GenVtx", field="y", bins=100, start=-0.02, stop=0.02, label=r"GenVtx $y$ [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
    }


def lepton_displacement_hists(coll=None, label=None, pos=None, only_categories=None):
    return {
        f"{label}_v0_origin": _hist(
            coll=coll, pos=pos, field="v0_origin_um", bins=100, start=0, stop=1e5,
            label=rf"{label} $v_0$ (origin) [$\mu m$]", cats=only_categories, samples=MC_SAMPLES
        ),
        f"{label}_v0_genvtx": _hist(
            coll=coll, pos=pos, field="v0_genvtx_um", bins=100, start=0, stop=2000,
            label=rf"{label} $v_0$ (GenVtx) [$\mu m$]", cats=only_categories, samples=MC_SAMPLES
        ),
        f"{label}_vx_vs_vy_origin": HistConf([
            Axis(coll=coll, pos=pos, field="genVtx_x", bins=100, start=-0.02, stop=0.02, label=rf"{label} $v_x$ (origin) [cm]"),
            Axis(coll=coll, pos=pos, field="genVtx_y", bins=100, start=-0.02, stop=0.02, label=rf"{label} $v_y$ (origin) [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_vx_vs_vy_genvtx": HistConf([
            Axis(coll=coll, pos=pos, field="v0_genvtx_x_um", bins=100, start=-200, stop=200, label=rf"{label} $v_x$ (GenVtx) [$\mu m$]"),
            Axis(coll=coll, pos=pos, field="v0_genvtx_y_um", bins=100, start=-200, stop=200, label=rf"{label} $v_y$ (GenVtx) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_parentpt_vs_v0": HistConf([
            Axis(coll=coll, pos=pos, field="uniqueGenPartMotherPt", bins=100, start=0, stop=500, label=rf"{label} direct parent $p_T$ [GeV]"),
            Axis(coll=coll, pos=pos, field="v0_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label} $v_0$ (GenVtx) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_parentpt_vs_d0": HistConf([
            Axis(coll=coll, pos=pos, field="uniqueGenPartMotherPt", bins=100, start=0, stop=500, label=rf"{label} direct parent $p_T$ [GeV]"),
            Axis(coll=coll, pos=pos, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label} $|d_0|$ [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
    }


def correlation_hists(channel, only_categories=None):
    (coll1, pos1, label1), (coll2, pos2, label2) = _get_legs_from_channel(channel)

    return {
        "v0_vs_v0_origin": HistConf([
            Axis(name="v0_vs_v0_origin_leg1", coll=coll1, pos=pos1, field="v0_origin_um", bins=100, start=0, stop=1e5, label=rf"{label1} $v_0$ (origin) [$\mu m$]"),
            Axis(name="v0_vs_v0_origin_leg2", coll=coll2, pos=pos2, field="v0_origin_um", bins=100, start=0, stop=1e5, label=rf"{label2} $v_0$ (origin) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        "v0_vs_v0_genvtx": HistConf([
            Axis(name="v0_vs_v0_genvtx_leg1", coll=coll1, pos=pos1, field="v0_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label1} $v_0$ (GenVtx) [$\mu m$]"),
            Axis(name="v0_vs_v0_genvtx_leg2", coll=coll2, pos=pos2, field="v0_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label2} $v_0$ (GenVtx) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        "v0_vs_v0_origin_extrap": HistConf([
            Axis(name="v0_vs_v0_origin_extrap_leg1", coll=coll1, pos=pos1, field="v0_extrap_origin_um", bins=100, start=0, stop=2000, label=rf"{label1} extrapolated $v_0$ (origin) [$\mu m$]"),
            Axis(name="v0_vs_v0_origin_extrap_leg2", coll=coll2, pos=pos2, field="v0_extrap_origin_um", bins=100, start=0, stop=2000, label=rf"{label2} extrapolated $v_0$ (origin) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        "v0_vs_v0_genvtx_extrap": HistConf([
            Axis(name="v0_vs_v0_genvtx_extrap_leg1", coll=coll1, pos=pos1, field="v0_extrap_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label1} extrapolated $v_0$ (GenVtx) [$\mu m$]"),
            Axis(name="v0_vs_v0_genvtx_extrap_leg2", coll=coll2, pos=pos2, field="v0_extrap_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label2} extrapolated $v_0$ (GenVtx) [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        "d0_vs_d0": HistConf([
            Axis(name="d0_vs_d0_leg1", coll=coll1, pos=pos1, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label1} $|d_0|$ [$\mu m$]"),
            Axis(name="d0_vs_d0_leg2", coll=coll2, pos=pos2, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label2} $|d_0|$ [$\mu m$]"),
        ], only_categories=only_categories),
        # systemboost_vs_v0_vs_v0 and systemboost_reco_vs_d0_vs_d0 are no longer populated (all NaNs)
        # "systemboost_vs_v0_vs_v0": HistConf([
        #     Axis(name="systemboost_pt_gen", coll="SystemBoost", field="pt_gen", bins=50, start=0, stop=500, label=r"System boost (gen) $p_T$ [GeV]"),
        #     Axis(name="systemboost_vs_v0_vs_v0_leg1", coll=coll1, pos=pos1, field="v0_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label1} $v_0$ (GenVtx) [$\mu m$]"),
        #     Axis(name="systemboost_vs_v0_vs_v0_leg2", coll=coll2, pos=pos2, field="v0_genvtx_um", bins=100, start=0, stop=2000, label=rf"{label2} $v_0$ (GenVtx) [$\mu m$]"),
        # ], only_categories=only_categories, only_samples=MC_SAMPLES),
        # "systemboost_reco_vs_d0_vs_d0": HistConf([
        #     Axis(name="systemboost_pt_reco", coll="SystemBoost", field="pt_reco", bins=50, start=0, stop=500, label=r"System boost (reco) $p_T$ [GeV]"),
        #     Axis(name="systemboost_reco_vs_d0_vs_d0_leg1", coll=coll1, pos=pos1, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label1} $|d_0|$ [$\mu m$]"),
        #     Axis(name="systemboost_reco_vs_d0_vs_d0_leg2", coll=coll2, pos=pos2, field="absd0_um", bins=100, start=0, stop=2000, label=rf"{label2} $|d_0|$ [$\mu m$]"),
        # ], only_categories=only_categories),
    }


def background_hists():
    abcd_pt_bins = [0, 90, 100, 140, 300, 400, 1e6] # 1e6 is just a really high number to simulate infinity
    abcd_d0_bins = [1, 1e1, 1e2, 5e2, 1e3, 5e3, 1e4, 5e4, 1e5]
    return {
        "abcd_ee": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e2_d0", coll="ElectronGood", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e1_pt", coll="ElectronGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Electron $p_T$"),
            ],
            only_categories=["ee"]
        ),
        "abcd_emu": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_d0", coll="MuonGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_pt", coll="MuonGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["emu"]
        ),
        "abcd_mumu": HistConf(
            [
                Axis(name="mu1_d0", coll="MuonGood", field="absd0_um", pos=0, bins=abcd_d0_bins, label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu2_d0", coll="MuonGood", field="absd0_um", pos=1, bins=abcd_d0_bins, label=rf"Subleading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_pt", coll="MuonGood", field="pt", pos=0, bins=abcd_pt_bins, label=rf"Leading Muon $p_T$"),
            ],
            only_categories=["mumu"]
        ),
        "d0d0_ee": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="e2_d0", coll="ElectronGood", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Electron $|d_0|$ [$\mu m$]")
            ],
            only_categories=["ee"]
        ),
        "d0d0_emu": HistConf(
            [
                Axis(name="e1_d0", coll="ElectronGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Electron $|d_0|$ [$\mu m$]"),
                Axis(name="mu1_d0", coll="MuonGood", field="absd0_um", pos=0, bins=100, start=0, stop=200, label=rf"Leading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["emu"]
        ),
        "d0d0_mumu": HistConf(
            [
                Axis(name="mu1_d0", coll="MuonGood", field="absd0_um", pos=0, bins=[0, 100, 1e5], label=rf"Leading Muon $|d_0|$ [$\mu m$]"),
                Axis(name="mu2_d0", coll="MuonGood", field="absd0_um", pos=1, bins=100, start=0, stop=200, label=rf"Subleading Muon $|d_0|$ [$\mu m$]")
            ],
            only_categories=["mumu"]
        )
    }

