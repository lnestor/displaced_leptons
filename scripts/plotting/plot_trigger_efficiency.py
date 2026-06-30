import argparse
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from scripts.coffea_file import CoffeaFile
from hist.intervals import clopper_pearson_interval


hep.style.use("CMS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--channel", required=True, choices=["ee", "emu", "mumu"])
    parser.add_argument("--trigger", required=True)
    parser.add_argument("--output", default="plot.png")
    parser.add_argument("--years", nargs="+")
    args = parser.parse_args()

    f = CoffeaFile(args.input)

    if args.channel == "ee":
        hist_name = "SubleadingElectron_pt"
    elif args.channel == "emu":
        hist_name = "LeadingElectron_pt"
    else:
        hist_name = "SubleadingMuon_pt"

    denom = f.get_total_hist(hist_name, "MET", args.years, args.channel)
    numer = f.get_total_hist(hist_name, "MET", args.years, f"{args.channel}_{args.trigger}")

    n = numer.values()
    d = denom.values()
    eff = np.where(d > 0, n / d, np.nan)
    lo, hi = clopper_pearson_interval(n, d)

    centers = denom.axes[0].centers
    widths = denom.axes[0].widths

    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=True)
    ax.errorbar(
        centers, eff,
        xerr=widths / 2,
        yerr=[eff - lo, hi - eff],
        fmt="o", color="black"
    )
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Efficiency")
    ax.set_xlabel(denom.axes[0].label)
    ax.set_title(args.trigger)
    fig.savefig(args.output, bbox_inches="tight")


if __name__ == "__main__":
    main()
