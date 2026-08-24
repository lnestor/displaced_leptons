import argparse
import os
import subprocess
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

MUON_HIST = "AllMuon_d0"
ELECTRON_HIST = "AllElectron_d0"
YEARS = ["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"]


def gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def extract_fit(h, fit_range):
    axis = h.axes[0]
    edges = np.asarray(axis.edges, dtype=np.float64)

    x_vals = 0.5 * (edges[:-1] + edges[1:])
    y_vals = h.values()
    y_errs = np.sqrt(h.variances())

    mask = (x_vals >= fit_range[0]) & (x_vals <= fit_range[1])
    x_vals, y_vals, y_errs = x_vals[mask], y_vals[mask], y_errs[mask]

    least_squares = LeastSquares(x_vals, y_vals, y_errs, gaussian)
    m = Minuit(least_squares, amp=y_vals.max(), mu=x_vals[np.argmax(y_vals)], sigma=5.0)
    m.limits["sigma"] = (0, None)
    m.migrad()
    m.hesse()

    amp = ufloat(m.values["amp"], m.errors["amp"])
    mean = ufloat(m.values["mu"], m.errors["mu"])
    sigma = ufloat(m.values["sigma"], m.errors["sigma"])
    chi2 = m.fmin.reduced_chi2

    return mean, sigma, amp, chi2


def average_smear_value(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def calc_smear_value(f, channel, hist_name, year, fit_bounds):
    fit_range = (-fit_bounds, fit_bounds)
    data_sample = {"emu": "MuonEG", "mumu": "Muon", "ee": "EGamma"}[channel]
    mc_sample = "TTbar" if channel == "emu" else "DY"

    h_data = f.get_total_hist(hist_name, samples=data_sample, category="pcr_absd0_um", years=year)
    h_mc = f.get_total_hist(hist_name, samples=mc_sample, category="pcr_absd0_um", years=year)

    mean_data, sigma_data, amp_data, chi2_data = extract_fit(h_data, fit_range)
    mean_mc, sigma_mc, amp_mc, chi2_mc = extract_fit(h_mc, fit_range)

    scale = h_data.values().sum() / h_mc.values().sum()

    if sigma_data.nominal_value**2 < sigma_mc.nominal_value**2:
        sigma_smear = None
    else:
        sigma_smear = usqrt(sigma_data**2 - sigma_mc**2)

    return {
        "channel": channel,
        "hist_name": hist_name,
        "year": year,
        "fit_range": fit_range,
        "h_data": h_data,
        "h_mc": h_mc,
        "scale": scale,
        "mean_data": mean_data,
        "sigma_data": sigma_data,
        "amp_data": amp_data,
        "chi2_data": chi2_data,
        "mean_mc": mean_mc,
        "sigma_mc": sigma_mc,
        "amp_mc": amp_mc,
        "chi2_mc": chi2_mc,
        "sigma": sigma_smear,
    }


def plot_smear_fit(result, output_dir):
    h_mc_scaled = result["h_mc"] * result["scale"]

    fig, ax = plt.subplots()
    plot_1d(result["h_data"], ax=ax)
    hep.histplot(h_mc_scaled, histtype="errorbar", ax=ax, flow="none", color="red")

    x_vals = np.linspace(result["fit_range"][0], result["fit_range"][1], 100)
    y_vals_data = gaussian(x_vals, result["amp_data"].n, result["mean_data"].n, result["sigma_data"].n)
    ax.plot(x_vals, y_vals_data, label="data fit")

    y_vals_mc = gaussian(x_vals, result["amp_mc"].n * result["scale"], result["mean_mc"].n, result["sigma_mc"].n)
    ax.plot(x_vals, y_vals_mc, label="mc fit", color="red")

    ax.legend()

    textstr = f"data chi2/ndof = {result['chi2_data']:.2f}\nmc chi2/ndof = {result['chi2_mc']:.2f}"
    ax.text(
        0.95, 0.95, textstr, transform=ax.transAxes,
        fontsize=10, verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    plotname = f"d0_fit_{result['channel']}_{result['hist_name']}_{result['year']}.png"
    fig.savefig(os.path.join(output_dir, plotname), bbox_inches="tight")
    plt.close(fig)


def print_table(console, title, headers, rows):
    table = Table(title=title)
    for header in headers:
        table.add_column(header)
    for row in rows:
        table.add_row(*row)

    console.print()
    console.print(table)


def escape_latex(value):
    return str(value).replace("_", r"\_")


LATEX_TEMPLATE = r"""\documentclass{{article}}
\usepackage{{booktabs}}
\pagestyle{{empty}}
\begin{{document}}
\begin{{tabular}}{{{col_spec}}}
\toprule
{header_row} \\
\midrule
{body_rows}
\bottomrule
\end{{tabular}}
\end{{document}}
"""


def save_latex_table(headers, rows, output_dir, filename):
    col_spec = "l" * len(headers)
    header_row = " & ".join(escape_latex(h) for h in headers)
    body_rows = "\n".join(
        " & ".join(escape_latex(c) for c in row) + r" \\" for row in rows
    )

    doc = LATEX_TEMPLATE.format(
        col_spec=col_spec, header_row=header_row, body_rows=body_rows
    )

    tex_path = os.path.join(output_dir, f"{filename}.tex")
    with open(tex_path, "w") as tex_file:
        tex_file.write(doc)

    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    pdf_path = os.path.join(output_dir, f"{filename}.pdf")
    png_path = os.path.join(output_dir, f"{filename}.png")
    subprocess.run(
        ["pdftoppm", "-png", "-r", "300", "-singlefile", pdf_path, os.path.join(output_dir, filename)],
        check=True,
    )
    subprocess.run(["convert", png_path, "-trim", "+repage", png_path], check=True)

    for ext in ("aux", "log", "pdf"):
        extra_path = os.path.join(output_dir, f"{filename}.{ext}")
        if os.path.exists(extra_path):
            os.remove(extra_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ee")
    parser.add_argument("--emu")
    parser.add_argument("--mumu")
    parser.add_argument("--fit-bounds", default=20, type=int)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--latex", action="store_true")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    if not args.ee and not args.emu and not args.mumu:
        print("You must pass at least one of --ee, --emu, or --mumu.")
        exit(1)

    if args.plot or args.latex:
        os.makedirs(args.output_dir, exist_ok=True)

    ele_sigmas = {y: [] for y in YEARS}
    mu_sigmas = {y: [] for y in YEARS}

    console = Console()

    if args.ee:
        f_ee = CoffeaFile(args.ee)
        ee_headers = ["Year", "Electron Sigma", "Electron Data Chi2", "Electron MC Chi2"]
        ee_rows = []

        for year in track(YEARS, description="Calculating ee channel..."):
            result = calc_smear_value(f_ee, "ee", "AllElectron_d0", year, args.fit_bounds)
            if args.plot:
                plot_smear_fit(result, args.output_dir)
            ee_rows.append([
                year,
                str(result["sigma"]) if result["sigma"] is not None else "N/A",
                f"{result['chi2_data']:.2f}",
                f"{result['chi2_mc']:.2f}",
            ])

            ele_sigmas[year].append(result["sigma"])

        print_table(console, "ee Details", ee_headers, ee_rows)
        if args.latex:
            save_latex_table(ee_headers, ee_rows, args.output_dir, "ee_details")

    if args.mumu:
        f_mumu = CoffeaFile(args.mumu)
        mumu_headers = ["Year", "Muon Sigma", "Muon Data Chi2", "Muon MC Chi2"]
        mumu_rows = []

        for year in track(YEARS, description="Calculating mumu channel..."):
            result = calc_smear_value(f_mumu, "mumu", "AllMuon_d0", year, args.fit_bounds)
            if args.plot:
                plot_smear_fit(result, args.output_dir)
            mumu_rows.append([
                year,
                str(result["sigma"]) if result["sigma"] is not None else "N/A",
                f"{result['chi2_data']:.2f}",
                f"{result['chi2_mc']:.2f}",
            ])

            mu_sigmas[year].append(result["sigma"])

        print_table(console, "mumu Details", mumu_headers, mumu_rows)
        if args.latex:
            save_latex_table(mumu_headers, mumu_rows, args.output_dir, "mumu_details")

    if args.emu:
        f_emu = CoffeaFile(args.emu)
        emu_headers = [
            "Year",
            "Electron Sigma", "Electron Data Chi2", "Electron MC Chi2",
            "Muon Sigma", "Muon Data Chi2", "Muon MC Chi2",
        ]
        emu_rows = []

        for year in track(YEARS, description="Calculating emu channel..."):
            ele_result = calc_smear_value(f_emu, "emu", "AllElectron_d0", year, args.fit_bounds)
            mu_result = calc_smear_value(f_emu, "emu", "AllMuon_d0", year, args.fit_bounds)
            if args.plot:
                plot_smear_fit(ele_result, args.output_dir)
                plot_smear_fit(mu_result, args.output_dir)
            emu_rows.append([
                year,
                str(ele_result["sigma"]) if ele_result["sigma"] is not None else "N/A",
                f"{ele_result['chi2_data']:.2f}",
                f"{ele_result['chi2_mc']:.2f}",
                str(mu_result["sigma"]) if mu_result["sigma"] is not None else "N/A",
                f"{mu_result['chi2_data']:.2f}",
                f"{mu_result['chi2_mc']:.2f}",
            ])

            ele_sigmas[year].append(ele_result["sigma"])
            mu_sigmas[year].append(mu_result["sigma"])

        print_table(console, "emu Details", emu_headers, emu_rows)
        if args.latex:
            save_latex_table(emu_headers, emu_rows, args.output_dir, "emu_details")

    avg_headers = ["Year", "Electron", "Muon"]
    avg_rows = []
    for year in YEARS:
        ele_avg = average_smear_value(ele_sigmas[year])
        mu_avg = average_smear_value(mu_sigmas[year])
        avg_rows.append([
            year,
            str(ele_avg) if ele_avg is not None else "N/A",
            str(mu_avg) if mu_avg is not None else "N/A",
        ])

    print_table(console, "Average d0 Smearing Values", avg_headers, avg_rows)
    if args.latex:
        save_latex_table(avg_headers, avg_rows, args.output_dir, "average_smearing")


if __name__ == "__main__":
    main()
