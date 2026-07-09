import argparse
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from scripts.coffea_file import CoffeaFile
from hist.intervals import clopper_pearson_interval


hep.style.use("CMS")


def cat_to_trigger(cat):
    # Categories are passes_<TRIGGER>, index 7 removes "passes_"
    return cat[7:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--channel", required=True, choices=["ee", "emu", "mumu"])
    parser.add_argument("--trigger", default="all")
    parser.add_argument("--years", nargs="+")
    parser.add_argument("--sample", default="MET")
    args = parser.parse_args()

    f = CoffeaFile(args.input)

    if args.channel == "ee":
        hist_name = "SubleadingElectron_pt"
    elif args.channel == "emu":
        hist_name = "LeadingElectron_pt"
    else:
        hist_name = "SubleadingMuon_pt"

    # Make sure trigger is in the file
    trigger_cats = [cat for cat in f.get_categories() if cat != "baseline"]
    triggers = [cat_to_trigger(cat) for cat in trigger_cats]
    if args.trigger != "all" and args.trigger not in triggers:
        print(f"ERROR: Trigger {args.trigger} not found. Choose from:")
        print("\n".join(f"  {trigger}" for trigger in sorted(triggers)))
        exit(1)

    if args.trigger != "all":
        trigger_cats = [args.trigger]


    for cat in trigger_cats:
        denom = f.get_total_hist(hist_name, args.sample, args.years, "baseline")
        numer = f.get_total_hist(hist_name, args.sample, args.years, cat)

        n = numer.values()
        d = denom.values()
        eff = np.where(d > 0, n / d, np.nan)
        lo, hi = clopper_pearson_interval(n, d)

        centers = denom.axes[0].centers
        widths = denom.axes[0].widths

        fig, ax = plt.subplots()
        hep.cms.label("Preliminary", ax=ax, data=False, com=13.6)
        ax.errorbar(
            centers, eff,
            xerr=widths / 2,
            yerr=[eff - lo, hi - eff],
            fmt="o", color="black"
        )
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Efficiency")
        ax.set_xlabel(denom.axes[0].label)
        ax.text(
            0.95, 0.05, cat_to_trigger(cat),
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize="small"
        )

        plot_name = f"plot_{cat_to_trigger(cat)}"
        fig.savefig(plot_name, bbox_inches="tight")


if __name__ == "__main__":
    main()
