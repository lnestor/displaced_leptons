import argparse

import hist
import matplotlib.pyplot as plt

from scripts.coffea_file import CoffeaFile
from scripts.plotting.common import SAMPLE_LABELS
from scripts.plotting.hist1d import plot_1d
from scripts.plotting.stack import plot_stack
from scripts.plotting.transforms import weighted_mean_profile

CATEGORY = "pcr_absd0_um"
MC_SAMPLES = ["DY", "Diboson", "SingleTop", "TTbar", "QCDEle", "QCDMu"]
INDIV_OBJECTS = {
    "ee": ["LeadingElectron", "SubleadingElectron"],
    "emu": ["LeadingElectron", "LeadingMuon"],
    "mumu": ["LeadingMuon", "SubleadingMuon"],
}
SAMPLE = {
    "ee": "EGamma",
    "emu": "MuonEG",
    "mumu": "Muon",
}


def get_hist_names(obj):
    return [f"{obj}_pt", f"{obj}_eta", f"{obj}_absd0", f"{obj}_absd0_uncorrected"]


def get_hists_if_present(f, hist_name, samples):
    hists = {}
    for sample in samples:
        h = f.get_total_hist(hist_name, samples=sample, category=CATEGORY)
        if isinstance(h, hist.Hist):
            hists[sample] = h
    return hists


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--channel", required=True, choices=["mumu", "ee", "emu"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lumi", type=float, help="Integrated luminosity in fb^-1")
    parser.add_argument("--com", type=float, default=13.6, help="Center-of-mass energy in TeV")
    args = parser.parse_args()

    f = CoffeaFile(args.input)
    style = dict(lumi=args.lumi, com=args.com)
    data_sample = SAMPLE[args.channel]

    hist_names = [name for obj in INDIV_OBJECTS[args.channel] for name in get_hist_names(obj)]
    for hist_name in hist_names:
        mc_hists = get_hists_if_present(f, hist_name, MC_SAMPLES)
        h_data = f.get_total_hist(hist_name, samples=data_sample, category=CATEGORY)

        fig, _, _ = plot_stack(h_data, mc_hists, ylog=True, ymin=0.02, ymax=7e6, **style)
        fig.savefig(f"{args.output_dir}/{args.channel}_pcr_{hist_name}.png", bbox_inches="tight")
        plt.close(fig)

    for obj in INDIV_OBJECTS[args.channel]:
        hist_name = f"{obj}_d0vsphi"

        mc_hists = get_hists_if_present(f, hist_name, MC_SAMPLES)
        h2d_data = f.get_total_hist(hist_name, samples=data_sample, category=CATEGORY)

        profiles = [weighted_mean_profile(h) for h in [h2d_data, *mc_hists.values()]]
        labels = ["Data", *(SAMPLE_LABELS[s] for s in mc_hists)]

        fig, _ = plot_1d(profiles, labels=labels, ylabel=h2d_data.axes[1].label, **style)
        fig.savefig(f"{args.output_dir}/{args.channel}_pcr_{hist_name}.png", bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
