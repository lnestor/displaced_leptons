import argparse
import matplotlib.pyplot as plt
import mplhep as hep

import sys
sys.path.append("scripts")
from coffea_file import CoffeaFile

hep.style.use("CMS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-c", "--category")
    parser.add_argument("-y", "--years", nargs="+")
    parser.add_argument("-s", "--sample")
    parser.add_argument("-o", "--output", default="cutflow.png")
    parser.add_argument("--efficiency", action="store_true")

    args = parser.parse_args()

    f = CoffeaFile(args.input)
    cutflow = f.get_cutflow(args.category, args.sample, args.years)
    labels = ["Total", *f.get_cut_labels(args.category)]

    if args.efficiency:
        cutflow = [c / cutflow[0] for c in cutflow]

    fig, ax = plt.subplots(figsize=(14,6))

    hep.cms.label("Preliminary", ax=ax, data=True, loc=0)
    hep.histplot(cutflow, ax=ax)

    ax.set_xlim(0, len(cutflow))
    ax.set_xticks(range(len(cutflow) + 1))
    ax.set_xticklabels([])
    ax.set_xticks([i + 0.70 for i in range(len(labels))], minor=True)
    ax.set_xticklabels(labels, rotation=25, ha="right", minor=True)
    ax.tick_params(axis="x", which="minor", length=0)
    ax.set_ylabel("Events")
    ax.set_yscale("log")

    fig.savefig(args.output, bbox_inches="tight")


if __name__ == "__main__":
    main()
