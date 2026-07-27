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


def hist_name_to_label(hist_name):
    if hist_name.startswith("Leading"):
        return "Leading"
    if hist_name.startswith("Subleading"):
        return "Subleading"
    return hist_name


def compute_efficiency(f, hist_name, sample, years, cat):
    denom = f.get_total_hist(hist_name, sample, years, "baseline")
    numer = f.get_total_hist(hist_name, sample, years, cat)

    n = numer.values()
    d = denom.values()
    eff = np.where(d > 0, n / d, np.nan)
    lo, hi = clopper_pearson_interval(n, d)

    return denom.axes[0], eff, lo, hi


def plot_curves(f, hist_names, sample, years, cat, suffix):
    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=False, com=13.6)

    xlabel = None
    xlim = None
    for hist_name in hist_names:
        axis, eff, lo, hi = compute_efficiency(f, hist_name, sample, years, cat)

        centers = axis.centers
        widths = axis.widths
        xlabel = axis.label
        edges = axis.edges
        xlim = (edges[0], edges[-1])

        ax.errorbar(
            centers, eff,
            xerr=widths / 2,
            yerr=[eff - lo, hi - eff],
            fmt="o", label=hist_name_to_label(hist_name),
        )

    ax.set_ylim(0, 1.1)
    ax.set_xlim(*xlim)
    ax.set_ylabel("Efficiency")
    ax.set_xlabel(xlabel)
    ax.text(
        0.95, 0.05, cat_to_trigger(cat),
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize="small"
    )
    if len(hist_names) > 1:
        ax.legend(loc="center left", fontsize="small")

    plot_name = f"plot_{cat_to_trigger(cat)}_{suffix}"
    fig.savefig(plot_name, bbox_inches="tight")
    plt.close(fig)


def plot_curves_all_triggers(f, hist_name, sample, years, trigger_cats, suffix):
    fig, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=False, com=13.6)

    xlabel = None
    xlim = None
    for cat in trigger_cats:
        axis, eff, lo, hi = compute_efficiency(f, hist_name, sample, years, cat)

        centers = axis.centers
        widths = axis.widths
        xlabel = axis.label
        edges = axis.edges
        xlim = (edges[0], edges[-1])

        ax.errorbar(
            centers, eff,
            xerr=widths / 2,
            yerr=[eff - lo, hi - eff],
            fmt="o", label=cat_to_trigger(cat),
        )

    ax.set_ylim(0, 1.1)
    ax.set_xlim(*xlim)
    ax.set_ylabel("Efficiency")
    ax.set_xlabel(xlabel)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize="small")

    plot_name = f"plot_all_triggers_{suffix}"
    fig.savefig(plot_name, bbox_inches="tight")
    plt.close(fig)


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
        pt_hist_name = "SubleadingElectron_pt"
        d0_hist_names = ["LeadingElectron_d0", "SubleadingElectron_d0"]
    elif args.channel == "emu":
        hist_name = "LeadingElectron_pt"
    else:
        hist_name = "SubleadingMuon_pt"

    trigger_cats = [cat for cat in f.get_categories() if cat != "baseline"]
    triggers = [cat_to_trigger(cat) for cat in trigger_cats]
    if args.trigger != "all" and args.trigger not in triggers:
        print(f"ERROR: Trigger {args.trigger} not found. Choose from:")
        print("\n".join(f"  {trigger}" for trigger in sorted(triggers)))
        exit(1)

    if args.trigger != "all":
        trigger_cats = [args.trigger]

    for cat in trigger_cats:
        # TODO: Make sure sample/year is in the file

        plot_curves(f, [pt_hist_name], args.sample, args.years, cat, "_pt")
        plot_curves(f, d0_hist_names, args.sample, args.years, cat, "_d0")

    plot_curves_all_triggers(f, pt_hist_name, args.sample, args.years, trigger_cats, "pt")
    for hist_name in d0_hist_names:
        plot_curves_all_triggers(
            f, hist_name, args.sample, args.years, trigger_cats,
            f"d0_{hist_name_to_label(hist_name).lower()}"
        )


if __name__ == "__main__":
    main()
