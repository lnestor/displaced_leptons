import argparse
import os

import numpy as np
import hist
import scipy.optimize
import matplotlib.pyplot as plt
import mplhep as hep
from hist import Hist
from iminuit import Minuit
from iminuit.cost import LeastSquares
from uncertainties import ufloat
from scripts.coffea_file import CoffeaFile

hep.style.use("CMS")

CAT = "pcr_absd0_um"
YEARS = ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]


def double_gaussian(x, mu, amp1, sigma1, amp2, sigma2):
    return (amp1 * np.exp(-0.5 * ((x - mu) / sigma1)**2)
            + amp2 * np.exp(-0.5 * ((x - mu) / sigma2)**2))


def kernel(x, q, s1, s2, seed=0):
    rng = np.random.default_rng(seed)
    n = len(x)
    u = rng.random(n)
    z = u < q
    return np.where(z, rng.normal(0, s1, n), rng.normal(0, s2, n))


def amp_to_q(amp1, sigma1, amp2, sigma2):
    """Mixture fraction (kernel's q) implied by a double_gaussian fit's
    peak-height amplitudes. Converts through component area (amp * sigma),
    since q is a fraction of area, not a fraction of peak height."""
    area1 = amp1 * sigma1
    area2 = amp2 * sigma2
    return area1 / (area1 + area2)


def extract_fit(h, fit_range):
    axis = h.axes[0]
    edges = np.asarray(axis.edges, dtype=np.float64)

    x_vals = 0.5 * (edges[:-1] + edges[1:])
    y_vals = h.values()
    y_errs = np.sqrt(h.variances())

    mask = (x_vals >= fit_range[0]) * (x_vals <= fit_range[1])
    x_vals, y_vals, y_errs = x_vals[mask], y_vals[mask], y_errs[mask]

    peak_amp = y_vals.max()
    peak_mu = x_vals[np.argmax(y_vals)]

    ls = LeastSquares(x_vals, y_vals, y_errs, double_gaussian)
    m = Minuit(
        ls, mu=peak_mu,
        amp1=0.7 * peak_amp, sigma1=3.0,
        amp2=0.3 * peak_amp, sigma2=10.0
    )
    m.limits["sigma1"] = (0, None)
    m.limits["sigma2"] = (0, None)
    m.migrad()
    m.hesse()

    amp1 = ufloat(m.values["amp1"], m.errors["amp1"])
    amp2 = ufloat(m.values["amp2"], m.errors["amp2"])
    mean = ufloat(m.values["mu"], m.errors["mu"])
    sigma1 = ufloat(m.values["sigma1"], m.errors["sigma1"])
    sigma2 = ufloat(m.values["sigma2"], m.errors["sigma2"])

    # Force sigma1 < sigma2
    if sigma1.nominal_value > sigma2.nominal_value:
        sigma1, sigma2 = sigma2, sigma1
        amp1, amp2 = amp2, amp1

    return {
        "mean": mean,
        "sigma1": sigma1,
        "amp1": amp1,
        "sigma2": sigma2,
        "amp2": amp2,
    }


def smear_hist(h_mc, q, s1, s2, seed=0):
    axis = h_mc.axes[0]
    edges = np.asarray(axis.edges, dtype=np.float64)

    x_vals = 0.5 * (edges[:-1] + edges[1:])
    y_vals = h_mc.values()

    x_mc_flat = np.repeat(x_vals, y_vals.astype(int))
    delta = kernel(x_mc_flat, q, s1, s2, seed=seed)
    x_smeared = x_mc_flat + delta

    h_smeared = Hist(hist.axis.Regular(len(edges) - 1, edges[0], edges[-1]))
    h_smeared.fill(x_smeared)
    return h_smeared


def find_residual(fit_data, h_mc, q, s1, s2, fit_range, seed=0):
    h_smeared = smear_hist(h_mc, q, s1, s2, seed=seed)
    fit_smeared = extract_fit(h_smeared, fit_range)

    q_smeared = amp_to_q(fit_smeared["amp1"], fit_smeared["sigma1"], fit_smeared["amp2"], fit_smeared["sigma2"])
    q_data = amp_to_q(fit_data["amp1"], fit_data["sigma1"], fit_data["amp2"], fit_data["sigma2"])

    residuals = [
        (fit_smeared["mean"].nominal_value - fit_data["mean"].nominal_value) / fit_data["mean"].std_dev,
        (fit_smeared["sigma1"].nominal_value - fit_data["sigma1"].nominal_value) / fit_data["sigma1"].std_dev,
        (fit_smeared["sigma2"].nominal_value - fit_data["sigma2"].nominal_value) / fit_data["sigma2"].std_dev,
        (q_smeared.nominal_value - q_data.nominal_value) / q_data.std_dev,
    ]
    return float(np.sum(np.square(residuals)))


def plot_smear_check(h_data, h_mc, h_smeared, channel, hist_name, year, output_dir):
    scale = h_data.values().sum() / h_mc.values().sum()

    fig, ax = plt.subplots()
    hep.histplot(h_data, histtype="errorbar", ax=ax, flow="none", color="black", label="Data")
    hep.histplot(h_mc * scale, histtype="errorbar", ax=ax, flow="none", color="red", label="MC")
    hep.histplot(h_smeared * scale, histtype="errorbar", ax=ax, flow="none", color="green", label="MC smeared")
    ax.legend()

    plotname = f"d0_smear_check_{channel}_{hist_name}_{year}.png"
    fig.savefig(os.path.join(output_dir, plotname), bbox_inches="tight")
    plt.close(fig)


def run(f, channel, hist_name, year, fit_bounds, output_dir):
    fit_range = (-fit_bounds, fit_bounds)
    data_sample = {"emu": "MuonEG", "mumu": "Muon", "ee": "EGamma"}[channel]
    mc_sample = "TTbar" if channel == "emu" else "DY"

    h_data = f.get_total_hist(hist_name, samples=data_sample, category=CAT, years=year)
    h_mc = f.get_total_hist(hist_name, samples=mc_sample, category=CAT, years=year)

    fit_data = extract_fit(h_data, fit_range)
    fit_mc = extract_fit(h_mc, fit_range)

    q0 = amp_to_q(fit_data["amp1"], fit_data["sigma1"], fit_data["amp2"], fit_data["sigma2"]).nominal_value
    s1_0 = np.sqrt(max(fit_data["sigma1"].nominal_value**2 - fit_mc["sigma1"].nominal_value**2, 0))
    s2_0 = np.sqrt(max(fit_data["sigma2"].nominal_value**2 - fit_mc["sigma2"].nominal_value**2, 0))

    def objective(params):
        q, s1, s2 = params
        if not (0 <= q <= 1) or s1 < 0 or s2 < 0:
            return np.inf
        return find_residual(fit_data, h_mc, q, s1, s2, fit_range)

    result = scipy.optimize.minimize(
        objective, x0=[q0, s1_0, s2_0], method="Nelder-Mead"
    )
    q_best, s1_best, s2_best = result.x

    print(f"[{channel} {hist_name} {year}] q={q_best:.4f} s1={s1_best:.4f} s2={s2_best:.4f}")

    h_smeared_best = smear_hist(h_mc, q_best, s1_best, s2_best)
    plot_smear_check(h_data, h_mc, h_smeared_best, channel, hist_name, year, output_dir)

    return q_best, s1_best, s2_best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ee")
    parser.add_argument("--emu")
    parser.add_argument("--mumu")
    parser.add_argument("--fit-bounds", default=20, type=int)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    if not args.ee and not args.emu and not args.mumu:
        print("You must pass at least one of --ee, --emu, or --mumu.")
        exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    if args.ee:
        f = CoffeaFile(args.ee)
        for year in YEARS:
            run(f, "ee", "AllElectron_d0", year, args.fit_bounds, args.output_dir)

    if args.emu:
        f = CoffeaFile(args.emu)
        for year in YEARS:
            run(f, "emu", "AllElectron_d0", year, args.fit_bounds, args.output_dir)
            run(f, "emu", "AllMuon_d0", year, args.fit_bounds, args.output_dir)

    if args.mumu:
        f = CoffeaFile(args.mumu)
        for year in YEARS:
            run(f, "mumu", "AllMuon_d0", year, args.fit_bounds, args.output_dir)

if __name__ == "__main__":
    main()
