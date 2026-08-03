import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from coffea_file import CoffeaFile
from asymmetric_uncertainty import a_u
from hist.intervals import poisson_interval
from lib.categories import CLOSURE_D0_SWEEP_VALS
from configs.common import MC_SAMPLES
import mplhep as hep

hep.style.use("CMS")

N_BAND_POINTS = 100


def get_ratio(counts):
    expected = counts["c"] * counts["b"] / counts["a"]
    actual = counts["d"]
    return actual / expected


def get_a_u(val):
    low, high = poisson_interval(np.atleast_1d(val))
    low, high = low[0], high[0]
    return a_u(val, high - val, val - low)


def get_weighted_a_u(sumw, sumw2):
    """Same idea as get_a_u, but for a weighted MC yield: scales a Poisson
    interval computed on the effective event count (sumw**2 / sumw2) back up
    to the weighted yield, rather than assuming raw integer counts.
    """
    if sumw2 == 0:
        return a_u(sumw, 0, 0)

    n_eff = sumw ** 2 / sumw2
    scale = sumw / n_eff
    low, high = poisson_interval(np.atleast_1d(n_eff))
    low, high = low[0], high[0]
    return a_u(sumw, (high - n_eff) * scale, (n_eff - low) * scale)


def get_bkg_a_u(f, category, years):
    sumw = 0.0
    sumw2 = 0.0
    for sample in MC_SAMPLES:
        try:
            sumw += f.get_count(category, sample, years)
            sumw2 += f.get_variance(category, sample, years)
        except ValueError:
            continue

    return get_weighted_a_u(sumw, sumw2)


def extrapolate(ratios, extrapolation_point):
    import ROOT
    from array import array

    d0 = CLOSURE_D0_SWEEP_VALS

    x_vals = [(d0[i + 1] + d0[i]) / 2 for i in range(len(d0) - 1)]
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("channel", choices=["ee", "emu", "mumu"])
    parser.add_argument("year", nargs="+", choices=["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix", "2024", "2025"])
    parser.add_argument("--plot", action="store_true", help="Save confidence interval plots for the extrapolated ratio.")
    parser.add_argument("--background", action="store_true", help="Compute background simulation yields instead of data. No plots are made in this mode.")
    parser.add_argument("--use-toys", action="store_true")
    parser.add_argument("--extrapolation-point", default=200)
    args = parser.parse_args()

    f = CoffeaFile(args.input)

    if args.background:
        def get_counts(category):
            return get_bkg_a_u(f, category, args.year)
    else:
        if args.channel == "ee":
            sample = "EGamma"
        elif args.channel == "emu":
            sample = "MuonEG"
        else:
            sample = "Muon"

        def get_counts(category):
            return get_a_u(f.get_count(category, sample, args.year))

    sweep1_counts = [
        {
            "a": get_counts("closure_low_leptona_prompt_a"),
            "b": get_counts("closure_low_leptona_prompt_b"),
            "c": get_counts(f"closure_low_leptona_prompt_c{i}"),
            "d": get_counts(f"closure_low_leptona_prompt_d{i}"),
        } for i in range(1, len(CLOSURE_D0_SWEEP_VALS))
    ]

    sweep2_counts = [
        {
            "a": get_counts("closure_low_leptonb_prompt_a"),
            "b": get_counts("closure_low_leptonb_prompt_b"),
            "c": get_counts(f"closure_low_leptonb_prompt_c{i}"),
            "d": get_counts(f"closure_low_leptonb_prompt_d{i}"),
        } for i in range(1, len(CLOSURE_D0_SWEEP_VALS))
    ]

    point1_counts = {
        "a": get_counts("closure_high_leptona_prompt_a"),
        "b": get_counts("closure_high_leptona_prompt_b"),
        "c": get_counts("closure_high_leptona_prompt_c"),
        "d": get_counts("closure_high_leptona_prompt_d"),
    }

    point2_counts = {
        "a": get_counts("closure_high_leptonb_prompt_a"),
        "b": get_counts("closure_high_leptonb_prompt_b"),
        "c": get_counts("closure_high_leptonb_prompt_c"),
        "d": get_counts("closure_high_leptonb_prompt_d"),
    }

    sweep1_ratios = [get_ratio(c) for c in sweep1_counts]
    sweep2_ratios = [get_ratio(c) for c in sweep2_counts]
    point1_ratio = get_ratio(point1_counts)
    point2_ratio = get_ratio(point2_counts)

    sweep1_result = extrapolate(sweep1_ratios, args.extrapolation_point)
    sweep2_result = extrapolate(sweep2_ratios, args.extrapolation_point)

    print("Sweep 1 (lepton a) ratios:")
    for x, ratio in zip(sweep1_result["x_vals"], sweep1_ratios):
        print(f"  d0 = {x:.1f} um: {ratio}")
    print(f"  extrapolated to {args.extrapolation_point} um: {sweep1_result['prediction']}")

    print("Sweep 2 (lepton b) ratios:")
    for x, ratio in zip(sweep2_result["x_vals"], sweep2_ratios):
        print(f"  d0 = {x:.1f} um: {ratio}")
    print(f"  extrapolated to {args.extrapolation_point} um: {sweep2_result['prediction']}")

    print(f"Point 1 (lepton a, high d0) ratio: {point1_ratio}")
    print(f"Point 2 (lepton b, high d0) ratio: {point2_ratio}")

    if args.plot and not args.background:
        year_label = "-".join(args.year)
        os.makedirs("plots/closure_test", exist_ok=True)
        plot_extrapolation(
            sweep1_result, args.extrapolation_point,
            f"plots/closure_test/{args.channel}_{year_label}_sweep1.png"
        )
        plot_extrapolation(
            sweep2_result, args.extrapolation_point,
            f"plots/closure_test/{args.channel}_{year_label}_sweep2.png"
        )

if __name__ == "__main__":
    main()
