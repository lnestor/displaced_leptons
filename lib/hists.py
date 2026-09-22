import numpy as np

from pocket_coffea.parameters.histograms import HistConf, Axis

from lib.configuration import MC_SAMPLES


def _zero_floor_bins(first_edge, high, growth=2):
    edges = [0.0, first_edge]
    while edges[-1] < high:
        edges.append(edges[-1] * growth)
    return edges


def _signed_zero_floor_bins(first_edge, high, growth=2):
    positive = _zero_floor_bins(first_edge, high, growth)
    return [-e for e in reversed(positive[1:])] + positive


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
        "InteractionPoint_r": _hist(coll="GenVtx", field="r", bins=120, start=0, stop=0.12, label=r"Interaction point $r$ [cm]", cats=only_categories, samples=MC_SAMPLES),
        "InteractionPoint_x_vs_y": HistConf([
            Axis(coll="GenVtx", field="x", bins=100, start=0.02, stop=0.11, label=r"Interaction point $x$ [cm]"),
            Axis(coll="GenVtx", field="y", bins=100, start=-0.025, stop=-0.005, label=r"Interaction point $y$ [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
    }


def lepton_displacement_hists(coll=None, label=None, pos=None, only_categories=None):
    return {
        f"{label}_lxy": HistConf([
            Axis(coll=coll, pos=pos, field="lxy", bins=_zero_floor_bins(5e-4, 16), label=rf"{label} $L_{{xy}}$ [cm]")
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_dx_vs_dy": HistConf([
            Axis(coll=coll, pos=pos, field="dx", bins=_signed_zero_floor_bins(5e-4, 16), label=rf"{label} $dx$ [cm]"),
            Axis(coll=coll, pos=pos, field="dy", bins=_signed_zero_floor_bins(5e-4, 16), label=rf"{label} $dy$ [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_parentpt_vs_lxy": HistConf([
            Axis(coll=coll, pos=pos, field="uniqueGenPartMotherPt", bins=100, start=0, stop=500, label=rf"{label} direct parent $p_T$ [GeV]"),
            Axis(coll=coll, pos=pos, field="lxy", bins=_zero_floor_bins(5e-4, 16), label=rf"{label} $L_{{xy}}$ [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        f"{label}_parentpt_vs_d0": HistConf([
            Axis(coll=coll, pos=pos, field="uniqueGenPartMotherPt", bins=100, start=0, stop=500, label=rf"{label} direct parent $p_T$ [GeV]"),
            Axis(coll=coll, pos=pos, field="absd0_um", bins=100, start=0, stop=600, label=rf"{label} $|d_0|$ [$\mu m$]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
    }


def correlation_hists(channel, only_categories=None):
    (coll1, pos1, label1), (coll2, pos2, label2) = _get_legs_from_channel(channel)

    return {
        "lxy_vs_lxy": HistConf([
            Axis(name="lxy_vs_lxy_leg1", coll=coll1, pos=pos1, field="lxy", bins=_zero_floor_bins(5e-4, 16), label=rf"{label1} $L_{{xy}}$ [cm]"),
            Axis(name="lxy_vs_lxy_leg2", coll=coll2, pos=pos2, field="lxy", bins=_zero_floor_bins(5e-4, 16), label=rf"{label2} $L_{{xy}}$ [cm]"),
        ], only_categories=only_categories, only_samples=MC_SAMPLES),
        # v0_vs_v0_genvtx_extrap disabled -- range unclear, add back if needed
        # "v0_vs_v0_genvtx_extrap": HistConf([
        #     Axis(name="v0_vs_v0_genvtx_extrap_leg1", coll=coll1, pos=pos1, field="v0_extrap_genvtx_um", bins=100, start=0, stop=600, label=rf"{label1} extrapolated $v_0$ (GenVtx) [$\mu m$]"),
        #     Axis(name="v0_vs_v0_genvtx_extrap_leg2", coll=coll2, pos=pos2, field="v0_extrap_genvtx_um", bins=100, start=0, stop=600, label=rf"{label2} extrapolated $v_0$ (GenVtx) [$\mu m$]"),
        # ], only_categories=only_categories, only_samples=MC_SAMPLES),
        "d0_vs_d0": HistConf([
            Axis(name="d0_vs_d0_leg1", coll=coll1, pos=pos1, field="absd0_um", bins=100, start=0, stop=300, label=rf"{label1} $|d_0|$ [$\mu m$]"),
            Axis(name="d0_vs_d0_leg2", coll=coll2, pos=pos2, field="absd0_um", bins=100, start=0, stop=300, label=rf"{label2} $|d_0|$ [$\mu m$]"),
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

