import argparse
import os

import correctionlib.schemav2 as cs
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np

from scripts.coffea_file import CoffeaFile
from scripts.fitting.double_gaussian import DoubleGaussian
from scripts.plotting.util import cms_loc_val

hep.style.use("CMS")

CAT = "pcr_absd0_um"
YEARS = ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024"]


# TODO: extract this into class
def _single_gaussian(x, mu, amp, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def plot_combined(h_data, fit_data, h_mc, fit_mc, fit_range, output_dir, suffix):
    scale = h_data.values().sum() / h_mc.values().sum()

    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=True, loc=cms_loc_val("exterior"), com=13.6)
    hep.histplot(h_data, histtype="errorbar", ax=ax, flow="none", color="black", label="Data")
    hep.histplot(h_mc * scale, histtype="errorbar", ax=ax, flow="none", color="red", label="MC")

    x_vals = np.linspace(fit_range[0], fit_range[1], 200)
    ax.plot(x_vals, fit_data.sample(x_vals), color="black", linestyle="--")
    ax.plot(x_vals, fit_mc.sample(x_vals) * scale, color="red", linestyle="--")

    ax.legend()

    plotname = f"combined_distributions_{suffix}.png"
    fig.savefig(os.path.join(output_dir, plotname), bbox_inches="tight")
    plt.close(fig)


def plot_single(h, fit, fit_range, output_dir, plotname):
    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=True, loc=cms_loc_val("exterior"), com=13.6)
    hep.histplot(h, histtype="errorbar", ax=ax, flow="none", color="black")

    x_vals = np.linspace(fit_range[0], fit_range[1], 200)
    y1 = _single_gaussian(x_vals, fit.mean, fit.amp1, fit.sigma1)
    y2 = _single_gaussian(x_vals, fit.mean, fit.amp2, fit.sigma2)

    ax.plot(x_vals, fit.sample(x_vals), color="black", linestyle="--", label="Total fit")
    ax.plot(x_vals, y1, color="blue", linestyle=":", label="Gaussian 1")
    ax.plot(x_vals, y2, color="orange", linestyle=":", label="Gaussian 2")
    ax.legend()

    textstr = "\n".join([
        f"sigma1 = {fit.sigma1:.2f} +/- {fit.sigma1_err:.2f}",
        f"sigma2 = {fit.sigma2:.2f} +/- {fit.sigma2_err:.2f}",
        f"q = {fit.q:.2f} +/- {fit.q_err:.2f}",
    ])
    ax.text(
        0.95, 0.95, textstr, transform=ax.transAxes,
        verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    fig.savefig(os.path.join(output_dir, plotname), bbox_inches="tight")
    plt.close(fig)


def get_hists(f_other, f_emu, hist_name, non_emu_data_sample, year):
    h_other_data = f_other.get_total_hist(hist_name, samples=non_emu_data_sample, category=CAT, years=year)
    h_emu_data = f_emu.get_total_hist(hist_name, samples="MuonEG", category=CAT, years=year)
    h_data = h_other_data + h_emu_data

    h_other_mc = f_other.get_total_hist(hist_name, samples="DY", category=CAT, years=year)
    h_emu_mc = f_emu.get_total_hist(hist_name, samples="TTbar", category=CAT, years=year)
    h_mc = h_other_mc + h_emu_mc

    return h_data, h_mc


def build_correction(fit_mc, fit_data, correction_name, n_bins=100):
    percentiles = np.linspace(0, 1, n_bins + 1)
    edges = fit_mc.inverse_cdf(percentiles)

    bin_centers = 0.5 * (percentiles[:-1] + percentiles[1:])
    content = fit_data.inverse_cdf(bin_centers)

    # TODO: real up/down variations; nom/up/down are currently identical
    binning = cs.Binning(
        nodetype="binning",
        input="dxybs",
        edges=list(edges),
        content=list(content),
        flow="clamp",
    )

    return cs.Correction(
        name=correction_name,
        version=1,
        inputs=[
            cs.Variable(name="variation", type="string", description="Variation: nom, up, or down"),
            cs.Variable(name="dxybs", type="real", description="Transverse impact parameter"),
        ],
        output=cs.Variable(
            name="dxybs_corrected", type="real", description="Corrected transverse impact parameter"
        ),
        data=cs.Category(
            nodetype="category",
            input="variation",
            content=[
                cs.CategoryItem(key="nom", value=binning),
                cs.CategoryItem(key="up", value=binning),
                cs.CategoryItem(key="down", value=binning),
            ],
        ),
    )


def save_corrections(corrections, output_dir):
    cset = cs.CorrectionSet(
        schema_version=2,
        description="dxybs corrections",
        corrections=corrections
    )

    with open(f"{output_dir}/d0_corrections.json", "w") as fout:
        fout.write(cset.model_dump_json(exclude_unset=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ee")
    parser.add_argument("--emu")
    parser.add_argument("--mumu")
    parser.add_argument("--fit-bounds", default=50, type=int)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    if not args.emu or not (args.ee or args.mumu):
        print("You must pass --emu along with at least one of --ee or --mumu.")
        exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    f_ee = CoffeaFile(args.ee) if args.ee else None
    f_emu = CoffeaFile(args.emu) if args.emu else None
    f_mumu = CoffeaFile(args.mumu) if args.mumu else None

    fit_range = (-args.fit_bounds, args.fit_bounds)
    corrections = []

    for year in YEARS:
        if f_ee and f_emu:
            h_data, h_mc = get_hists(f_ee, f_emu, hist_name="AllElectron_d0", non_emu_data_sample="EGamma", year=year)

            fit_data, chi2_data = DoubleGaussian.fit(h_data, fit_range)
            fit_mc, chi2_mc = DoubleGaussian.fit(h_mc, fit_range)

            correction_name = f"electron_d0_correction_{year}"
            corr = build_correction(fit_mc, fit_data, correction_name)
            corrections.append(corr)

            plot_combined(h_data, fit_data, h_mc, fit_mc, fit_range, args.output_dir, f"ele_{year}")
            plot_single(h_data, fit_data, fit_range, args.output_dir, f"single_data_ele_{year}.png")
            plot_single(h_mc, fit_mc, fit_range, args.output_dir, f"single_mc_ele_{year}.png")
        else:
            print("Missing --ee and/or --emu: skipping electron fit.")

        if f_mumu and f_emu:
            h_data, h_mc = get_hists(f_mumu, f_emu, hist_name="AllMuon_d0", non_emu_data_sample="Muon", year=year)

            fit_data, chi2_data = DoubleGaussian.fit(h_data, fit_range)
            fit_mc, chi2_mc = DoubleGaussian.fit(h_mc, fit_range)

            correction_name = f"muon_d0_correction_{year}"
            corr = build_correction(fit_mc, fit_data, correction_name)
            corrections.append(corr)

            plot_combined(h_data, fit_data, h_mc, fit_mc, fit_range, args.output_dir, f"mu_{year}")
            plot_single(h_data, fit_data, fit_range, args.output_dir, f"single_data_mu_{year}.png")
            plot_single(h_mc, fit_mc, fit_range, args.output_dir, f"single_mc_mu_{year}.png")
        else:
            print("Missing --mumu and/or --emu: skipping muon fit.")

    save_corrections(corrections, args.output_dir)


if __name__ == "__main__":
    main()
