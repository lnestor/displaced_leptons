import argparse
import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from coffea_file import CoffeaFile
from asymmetric_uncertainty import a_u
from hist.intervals import poisson_interval
import mplhep as hep

hep.style.use("CMS")

N_BAND_POINTS = 100

# Must match sweep_axis1_edges in configs/specific/config_*_closure_test.py
CLOSURE_D0_SWEEP_VALS = [20, 30, 40, 50, 60, 70, 80, 90, 100]

CHANNEL_LATEX_LABELS = {
    "ee": "ee",
    "emu": r"e$\mu$",
    "mumu": r"$\mu\mu$",
}

MODE_KEYS = ["bkg"]

MODE_CONSOLE_LABELS = {}

MODE_LATEX_LABELS = {}


def get_ratio(counts):
    """Returns None if the ABCD estimate or its "a" denominator is exactly
    zero (e.g. zero events observed and zero events expected in a sideband),
    since the ratio is then undefined rather than a genuine measurement.
    """
    try:
        expected = counts["c"] * counts["b"] / counts["a"]
        return counts["d"] / expected
    except ZeroDivisionError:
        return None


def get_weighted_a_u(sumw, sumw2):
    """Scales a Poisson interval computed on the effective event count
    (sumw**2 / sumw2) back up to the weighted yield, rather than assuming
    raw integer counts.
    """
    if sumw2 == 0:
        return a_u(sumw, 0, 0)

    n_eff = sumw ** 2 / sumw2
    scale = sumw / n_eff
    low, high = poisson_interval(np.atleast_1d(n_eff))
    low, high = low[0], high[0]
    return a_u(sumw, (high - n_eff) * scale, (n_eff - low) * scale)


def get_bkg_a_u(f, category, years, samples):
    sumw = 0.0
    sumw2 = 0.0
    for sample in samples:
        try:
            sumw += f.get_count(category, sample, years)
            sumw2 += f.get_variance(category, sample, years)
        except ValueError:
            continue

    return get_weighted_a_u(sumw, sumw2)


def extrapolate(x_vals, ratios, extrapolation_point):
    import ROOT
    from array import array

    y_vals = [ratio.value for ratio in ratios]
    y_err_high = [ratio.plus for ratio in ratios]
    y_err_low = [ratio.minus for ratio in ratios]

    graph = ROOT.TGraphAsymmErrors(
        len(x_vals),
        array('d', x_vals),
        array('d', y_vals),
        array('d', [0.0] * len(x_vals)),
        array('d', [0.0] * len(x_vals)),
        array('d', y_err_low),
        array('d', y_err_high)
    )

    fit = ROOT.TF1("fit", "pol1", 0, extrapolation_point)
    fit_result = graph.Fit(fit, "SFEM")

    prediction = fit.Eval(extrapolation_point)

    err = array('d', [0.0])
    fit_result.GetConfidenceIntervals(
        1, 1, 1,
        array('d', [extrapolation_point]),
        err,
        0.6827, False
    )

    band_x = [extrapolation_point * i / (N_BAND_POINTS - 1) for i in range(N_BAND_POINTS)]
    band_y = [fit.Eval(x) for x in band_x]

    band_err_1sigma = array('d', [0.0] * N_BAND_POINTS)
    fit_result.GetConfidenceIntervals(N_BAND_POINTS, 1, N_BAND_POINTS, array('d', band_x), band_err_1sigma, 0.6827, False)

    band_err_2sigma = array('d', [0.0] * N_BAND_POINTS)
    fit_result.GetConfidenceIntervals(N_BAND_POINTS, 1, N_BAND_POINTS, array('d', band_x), band_err_2sigma, 0.9545, False)

    band = {
        "x": band_x,
        "y": band_y,
        "err_1sigma": list(band_err_1sigma),
        "err_2sigma": list(band_err_2sigma),
    }

    fit_params = {
        "p0": fit.GetParameter(0),
        "p1": fit.GetParameter(1),
        "chi2": fit.GetChisquare(),
        "ndf": fit.GetNDF(),
        "prob": fit.GetProb(),
    }

    return {
        "prediction": a_u(prediction, err[0], err[0]),
        "x_vals": x_vals,
        "y_vals": y_vals,
        "y_err_low": y_err_low,
        "y_err_high": y_err_high,
        "band": band,
        "fit_params": fit_params,
    }


def plot_extrapolation(result, extrapolation_point, output_path):
    band = result["band"]
    fit_params = result["fit_params"]

    fig, ax = plt.subplots()
    hep.cms.label("All Run 3", data=True, ax=ax, com=13.6)

    ax.fill_between(
        band["x"],
        [y - e for y, e in zip(band["y"], band["err_2sigma"])],
        [y + e for y, e in zip(band["y"], band["err_2sigma"])],
        color="#ffff00", label="95% CL"
    )
    ax.fill_between(
        band["x"],
        [y - e for y, e in zip(band["y"], band["err_1sigma"])],
        [y + e for y, e in zip(band["y"], band["err_1sigma"])],
        color="#00ff00", label="68% CL"
    )
    ax.plot(band["x"], band["y"], color="#ff0000", linewidth=1)

    ax.errorbar(
        result["x_vals"], result["y_vals"],
        yerr=[result["y_err_low"], result["y_err_high"]],
        fmt="ko", markersize=4, capsize=3
    )

    ax.set_xlim(0, extrapolation_point)
    ax.set_ylim(0, 6)
    ax.set_xlabel(r"Prompt lepton $|d_0|$ [$\mu m$]")
    ax.set_ylabel("Actual/estimate ratios")

    stat_text = (
        f"chi2 / ndf = {fit_params['chi2']:.3f} / {fit_params['ndf']}\n"
        f"Prob = {fit_params['prob']:.3f}\n"
        f"p0 = {fit_params['p0']:.4f}\n"
        f"p1 = {fit_params['p1']:.5f}"
    )
    ax.text(
        0.97, 0.97, stat_text, transform=ax.transAxes, ha="right", va="top",
        fontsize=8, bbox=dict(facecolor="white", edgecolor="black")
    )

    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def compute_closure_results(get_counts, extrapolation_point):
    d0 = CLOSURE_D0_SWEEP_VALS
    all_x = [(d0[i + 1] + d0[i]) / 2 for i in range(len(d0) - 1)]

    sweep1_counts = [
        {
            "a": get_counts("closure_sweep_l1_a"),
            "b": get_counts("closure_sweep_l1_b"),
            "c": get_counts(f"closure_sweep_l1_c{i}"),
            "d": get_counts(f"closure_sweep_l1_d{i}"),
        } for i in range(1, len(d0))
    ]

    sweep2_counts = [
        {
            "a": get_counts("closure_sweep_l2_a"),
            "b": get_counts("closure_sweep_l2_b"),
            "c": get_counts(f"closure_sweep_l2_c{i}"),
            "d": get_counts(f"closure_sweep_l2_d{i}"),
        } for i in range(1, len(d0))
    ]

    point1_counts = {
        "a": get_counts("closure_point_l1_a"),
        "b": get_counts("closure_point_l1_b"),
        "c": get_counts("closure_point_l1_c"),
        "d": get_counts("closure_point_l1_d"),
    }

    point2_counts = {
        "a": get_counts("closure_point_l2_a"),
        "b": get_counts("closure_point_l2_b"),
        "c": get_counts("closure_point_l2_c"),
        "d": get_counts("closure_point_l2_d"),
    }

    sweep1_ratios_raw = [get_ratio(c) for c in sweep1_counts]
    sweep2_ratios_raw = [get_ratio(c) for c in sweep2_counts]

    sweep1_x = [x for x, r in zip(all_x, sweep1_ratios_raw) if r is not None]
    sweep1_ratios = [r for r in sweep1_ratios_raw if r is not None]
    sweep2_x = [x for x, r in zip(all_x, sweep2_ratios_raw) if r is not None]
    sweep2_ratios = [r for r in sweep2_ratios_raw if r is not None]

    point1_ratio = get_ratio(point1_counts)
    point2_ratio = get_ratio(point2_counts)

    sweep1_result = extrapolate(sweep1_x, sweep1_ratios, extrapolation_point) if sweep1_ratios else None
    sweep2_result = extrapolate(sweep2_x, sweep2_ratios, extrapolation_point) if sweep2_ratios else None

    averaged_sweep_ratio = (
        (sweep1_result["prediction"] + sweep2_result["prediction"]) / 2
        if sweep1_result is not None and sweep2_result is not None else None
    )
    averaged_point_ratio = (
        (point1_ratio + point2_ratio) / 2
        if point1_ratio is not None and point2_ratio is not None else None
    )

    return {
        "sweep1_ratios": sweep1_ratios,
        "sweep2_ratios": sweep2_ratios,
        "sweep1_result": sweep1_result,
        "sweep2_result": sweep2_result,
        "point1_ratio": point1_ratio,
        "point2_ratio": point2_ratio,
        "averaged_sweep_ratio": averaged_sweep_ratio,
        "averaged_point_ratio": averaged_point_ratio,
    }


def print_closure_results(label, results, extrapolation_point):
    print(f"=== {label} ===")

    for name, key in [("Sweep 1 (lepton a)", "sweep1"), ("Sweep 2 (lepton b)", "sweep2")]:
        result = results[f"{key}_result"]
        print(f"{name} ratios:")
        if result is None:
            print("  no valid d0 bins (all undefined)")
            continue
        for x, ratio in zip(result["x_vals"], results[f"{key}_ratios"]):
            print(f"  d0 = {x:.1f} um: {ratio}")
        print(f"  extrapolated to {extrapolation_point} um: {result['prediction']}")

    print(f"Averaged sweep ratio (extrapolated to {extrapolation_point} um): {results['averaged_sweep_ratio']}")

    print(f"Point 1 (lepton a, high d0) ratio: {results['point1_ratio']}")
    print(f"Point 2 (lepton b, high d0) ratio: {results['point2_ratio']}")
    print(f"Averaged point ratio: {results['averaged_point_ratio']}")
    print()


def compute_channel_results(input_path, channel, years, extrapolation_point, samples):
    f = CoffeaFile(input_path)

    def get_bkg_counts(category):
        return get_bkg_a_u(f, category, years, samples)

    get_counts_by_mode = {
        "bkg": get_bkg_counts,
    }

    results_by_mode = {}
    for mode in MODE_KEYS:
        results = compute_closure_results(get_counts_by_mode[mode], extrapolation_point)
        results_by_mode[mode] = results
        print_closure_results(f"{channel}: {MODE_CONSOLE_LABELS[mode]}", results, extrapolation_point)

    return results_by_mode


def format_au_latex(value, decimals=1):
    if value is None:
        return "N/A"

    fmt = f"{{:.{decimals}f}}"
    central = fmt.format(round(value.value, decimals))
    plus = fmt.format(round(value.plus, decimals))
    minus = fmt.format(round(value.minus, decimals))

    if plus == minus:
        return f"${central} \\pm {plus}$"
    return f"${central}^{{+{plus}}}_{{-{minus}}}$"


def build_sweep_table(channel_results, extrapolation_point):
    channels = list(channel_results.keys())

    lines = [
        r"\begin{tabular}{lccc}",
        r"\toprule",
        " & " + " & ".join(MODE_LATEX_LABELS[mode] for mode in MODE_KEYS) + r" \\",
        r"\midrule",
    ]
    for channel in channels:
        results_by_mode = channel_results[channel]
        row = [CHANNEL_LATEX_LABELS[channel]]
        row.extend(format_au_latex(results_by_mode[mode]["averaged_sweep_ratio"]) for mode in MODE_KEYS)
        lines.append(" & ".join(row) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


def build_points_table(channel_results):
    channels = list(channel_results.keys())
    point_cols = list(MODE_KEYS)

    lines = [
        r"\begin{tabular}{l" + "c" * (2 * len(point_cols)) + "}",
        r"\toprule",
        " & \\multicolumn{"
        + str(len(point_cols))
        + "}{c}{Sideband 1} & \\multicolumn{"
        + str(len(point_cols))
        + r"}{c}{Sideband 2} \\",
        f"\\cmidrule(lr){{2-{1 + len(point_cols)}}} \\cmidrule(lr){{{2 + len(point_cols)}-{1 + 2 * len(point_cols)}}}",
        " & " + " & ".join([MODE_LATEX_LABELS[mode] for mode in point_cols] * 2) + r" \\",
        r"\midrule",
    ]
    for channel in channels:
        results_by_mode = channel_results[channel]
        row = [CHANNEL_LATEX_LABELS[channel]]
        for point_key in ["point1_ratio", "point2_ratio"]:
            row.extend(format_au_latex(results_by_mode[mode][point_key]) for mode in point_cols)
        lines.append(" & ".join(row) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


def render_latex_table_to_png(table_body, output_stem, dpi=300):
    tex_content = (
        "\\documentclass[10pt]{article}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage[paperwidth=60cm,paperheight=60cm,margin=1cm]{geometry}\n"
        "\\pagestyle{empty}\n"
        "\\begin{document}\n"
        f"{table_body}\n"
        "\\end{document}\n"
    )

    output_dir = os.path.dirname(output_stem) or "."
    stem_name = os.path.basename(output_stem)
    tex_path = os.path.join(output_dir, f"{stem_name}.tex")
    with open(tex_path, "w") as fh:
        fh.write(tex_content)

    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", output_dir, tex_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )

    pdf_path = os.path.join(output_dir, f"{stem_name}.pdf")
    raw_png_stem = os.path.join(output_dir, f"{stem_name}_raw")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf_path, raw_png_stem], check=True)

    raw_png_path = f"{raw_png_stem}-1.png"
    final_png_path = f"{output_stem}.png"
    subprocess.run(
        ["convert", raw_png_path, "-trim", "+repage", "-bordercolor", "white", "-border", "20", final_png_path],
        check=True,
    )

    os.remove(raw_png_path)
    for ext in (".aux", ".log"):
        aux_path = os.path.join(output_dir, f"{stem_name}{ext}")
        if os.path.exists(aux_path):
            os.remove(aux_path)

    return final_png_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("year", nargs="+", choices=["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"])
    parser.add_argument("--ee", help="Path to the merged coffea file for the ee channel.")
    parser.add_argument("--emu", help="Path to the merged coffea file for the emu channel.")
    parser.add_argument("--mumu", help="Path to the merged coffea file for the mumu channel.")
    parser.add_argument("--plot", action="store_true", help="Save confidence interval plots for the extrapolated data ratio.")
    parser.add_argument("--use-toys", action="store_true")
    parser.add_argument("--extrapolation-point", default=200)
    parser.add_argument("--output-dir", default="plots/closure_test")
    parser.add_argument("--samples", required=True, help="Comma-separated sample names as stored in the coffea file, e.g. TTbar or DY__ee,DY__mumu")
    parser.add_argument("--label", required=True, help="Human-readable label for this sample group, used in console output and table headers.")
    args = parser.parse_args()

    samples = [s.strip() for s in args.samples.split(",")]
    MODE_CONSOLE_LABELS["bkg"] = args.label
    MODE_LATEX_LABELS["bkg"] = args.label

    channel_inputs = {
        channel: path
        for channel, path in [("ee", args.ee), ("emu", args.emu), ("mumu", args.mumu)]
        if path
    }
    if not channel_inputs:
        parser.error("at least one of --ee, --emu, --mumu must be given")

    os.makedirs(args.output_dir, exist_ok=True)

    channel_results = {}
    for channel, input_path in channel_inputs.items():
        channel_results[channel] = compute_channel_results(
            input_path, channel, args.year, args.extrapolation_point, samples
        )

    sweep_table = build_sweep_table(channel_results, args.extrapolation_point)
    points_table = build_points_table(channel_results)

    sweep_tex_path = os.path.join(args.output_dir, "sweep_table.tex")
    points_tex_path = os.path.join(args.output_dir, "points_table.tex")
    with open(sweep_tex_path, "w") as fh:
        fh.write(sweep_table + "\n")
    with open(points_tex_path, "w") as fh:
        fh.write(points_table + "\n")
    print(f"Wrote {sweep_tex_path}")
    print(f"Wrote {points_tex_path}")

    sweep_png_path = render_latex_table_to_png(sweep_table, os.path.join(args.output_dir, "sweep_table"))
    points_png_path = render_latex_table_to_png(points_table, os.path.join(args.output_dir, "points_table"))
    print(f"Rendered {sweep_png_path}")
    print(f"Rendered {points_png_path}")

    if args.plot:
        year_label = "-".join(args.year)
        for channel, results_by_mode in channel_results.items():
            bkg_results = results_by_mode["bkg"]
            if bkg_results["sweep1_result"] is not None:
                plot_extrapolation(
                    bkg_results["sweep1_result"], args.extrapolation_point,
                    os.path.join(args.output_dir, f"{channel}_{year_label}_sweep1.png")
                )
            if bkg_results["sweep2_result"] is not None:
                plot_extrapolation(
                    bkg_results["sweep2_result"], args.extrapolation_point,
                    os.path.join(args.output_dir, f"{channel}_{year_label}_sweep2.png")
                )

if __name__ == "__main__":
    main()
