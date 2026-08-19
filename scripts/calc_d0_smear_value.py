import argparse
import numpy as np
from coffea_file import CoffeaFile
from uncertainties import ufloat
from uncertainties.umath import sqrt as usqrt
from iminuit import Minuit
from iminuit.cost import LeastSquares
import matplotlib.pyplot as plt
import mplhep as hep
from scripts.plotting.plot_1d import plot_1d
from rich.progress import track
from rich.console import Console
from rich.table import Table

FIT_RANGE = (-20, 20)
MUON_HIST = "AllMuon_d0"
ELECTRON_HIST = "AllElectron_d0"
YEARS = ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]


def gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def extract_fit(h):
    axis = h.axes[0]
    edges = np.asarray(axis.edges, dtype=np.float64)

    x_vals = 0.5 * (edges[:-1] + edges[1:])
    y_vals = h.values()
    y_errs = np.sqrt(h.variances())

    mask = (x_vals >= FIT_RANGE[0]) & (x_vals <= FIT_RANGE[1])
    x_vals, y_vals, y_errs = x_vals[mask], y_vals[mask], y_errs[mask]

    least_squares = LeastSquares(x_vals, y_vals, y_errs, gaussian)
    m = Minuit(least_squares, amp=y_vals.max(), mu=x_vals[np.argmax(y_vals)], sigma=5.0)
    m.limits["sigma"] = (0, None)
    m.migrad()
    m.hesse()

    amp = ufloat(m.values["amp"], m.errors["amp"])
    mean = ufloat(m.values["mu"], m.errors["mu"])
    sigma = ufloat(m.values["sigma"], m.errors["sigma"])

    return mean, sigma, amp


def average_smear_value(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def calc_smear_value(f, channel, hist_name, data_sample, mc_sample, year):
    h_data = f.get_total_hist(hist_name, samples=data_sample, category="pcr_absd0_um", years=year)
    h_mc = f.get_total_hist(hist_name, samples=mc_sample, category="pcr_absd0_um", years=year)

    mean_data, sigma_data, amp_data = extract_fit(h_data)
    mean_mc, sigma_mc, amp_mc = extract_fit(h_mc)

    scale = h_data.values().sum() / h_mc.values().sum()
    h_mc_scaled = h_mc * scale

    fig, ax = plt.subplots()
    plot_1d(h_data, ax=ax)
    hep.histplot(h_mc_scaled, histtype="errorbar", ax=ax, flow="none", color="red")

    x_vals = np.linspace(FIT_RANGE[0], FIT_RANGE[1], 100)
    y_vals_data = gaussian(x_vals, amp_data.n, mean_data.n, sigma_data.n)
    ax.plot(x_vals, y_vals_data, label="data fit")

    y_vals_mc = gaussian(x_vals, amp_mc.n * scale, mean_mc.n, sigma_mc.n)
    ax.plot(x_vals, y_vals_mc, label="mc fit", color="red")

    ax.legend()

    plotname = f"d0_fit_{channel}_{hist_name}_{year}.png"
    fig.savefig(plotname, bbox_inches="tight")

    if sigma_data.nominal_value**2 < sigma_mc.nominal_value**2:
        return None
    else:
        sigma_smear = usqrt(sigma_data**2 - sigma_mc**2)
        return sigma_smear

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ee")
    parser.add_argument("--emu")
    parser.add_argument("--mumu")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    if not args.ee and not args.emu and not args.mumu:
        print("You must pass at least one of --ee, --emu, or --mumu.")
        exit(1)

    ele_sigmas = {y: [] for y in YEARS}
    mu_sigmas = {y: [] for y in YEARS}

    if args.ee:
        f_ee = CoffeaFile(args.ee)
        for year in track(YEARS, description="Calculating ee channel..."):
            ele_sigmas[year].append(calc_smear_value(f_ee, "ee", "AllElectron_d0", "EGamma", "DY", year))

    if args.mumu:
        f_mumu = CoffeaFile(args.mumu)
        for year in track(YEARS, description="Calculating mumu channel..."):
            mu_sigmas[year].append(calc_smear_value(f_mumu, "mumu", "AllMuon_d0", "Muon", "DY", year))

    if args.emu:
        f_emu = CoffeaFile(args.emu)
        for year in track(YEARS, description="Calculating emu channel..."):
            ele_sigmas[year].append(calc_smear_value(f_emu, "emu", "AllElectron_d0", "MuonEG", "TTbar", year))
            mu_sigmas[year].append(calc_smear_value(f_emu, "emu", "AllMuon_d0", "MuonEG", "TTbar", year))

    table = Table(title="Average d0 Smearing Values")
    table.add_column("Year")
    table.add_column("Electron")
    table.add_column("Muon")
    for year in YEARS:
        ele_avg = average_smear_value(ele_sigmas[year])
        mu_avg = average_smear_value(mu_sigmas[year])
        table.add_row(
            year,
            str(ele_avg) if ele_avg is not None else "N/A",
            str(mu_avg) if mu_avg is not None else "N/A",
        )

    console = Console()
    console.print()
    console.print(table)


if __name__ == "__main__":
    main()
