import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from coffea.util import load

hep.style.use("CMS")

# Ordered bottom-to-top in the stack
SAMPLE_GROUPS = [
    {
        "label": "QCD",
        "color": "#92dadd",
        "samples": [
            "QCD_Pt-15to20_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-20to30_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-30to50_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-50to80_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-80to120_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-120to170_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-170to300_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-300toInf_EMEnriched_TuneCP5_13TeV-pythia8",
            "QCD_Pt-15To20_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-20To30_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-30To50_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-50To80_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-80To120_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-120To170_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-170To300_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-300To470_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-470To600_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-600To800_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-800To1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
            "QCD_Pt-1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8",
        ],
    },
    {
        "label": "Diboson",
        "color": "#bd1f01",
        "samples": [
            "WW_TuneCP5_13TeV-pythia8",
            "WZ_TuneCP5_13TeV-pythia8",
            "ZZ_TuneCP5_13TeV-pythia8",
        ],
    },
    {
        "label": "Single Top",
        "color": "#94a4a2",
        "samples": [
            "ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8",
            "ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8",
            "ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8",
            "ST_tW_top_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8",
            "ST_tW_antitop_5f_NoFullyHadronicDecays_TuneCP5_13TeV-powheg-pythia8",
        ],
    },
    {
        "label": "DY+jets",
        "color": "#ffa90e",
        "samples": [
            "DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8",
            "DYJetsToLL_M-10to50_TuneCP5_13TeV-madgraphMLM-pythia8",
        ],
    },
    {
        "label": r"t$\bar{\mathrm{t}}$",
        "color": "#3f90da",
        "samples": [
            "TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8",
            "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8",
            "TTToHadronic_TuneCP5_13TeV-powheg-pythia8",
        ],
    },
]

VARIABLES = {
    "Electron_pt":  {"xlabel": r"Electron $p_T$ [GeV]",      "log_y": False, "xlim": None},
    "Electron_eta": {"xlabel": r"Electron $\eta$",            "log_y": False, "xlim": None},
    "Electron_d0":  {"xlabel": r"Electron $|d_0|$ [$\mu$m]", "log_y": True,  "xlim": (0, 2000)},
    "Muon_pt":      {"xlabel": r"Muon $p_T$ [GeV]",          "log_y": False, "xlim": None},
    "Muon_eta":     {"xlabel": r"Muon $\eta$",                "log_y": False, "xlim": None},
    "Muon_d0":      {"xlabel": r"Muon $|d_0|$ [$\mu$m]",     "log_y": True,  "xlim": (0, 2000)},
}


def get_group_values(var_data, sample_names, category):
    values = None
    edges = None
    for sample, datasets in var_data.items():
        if sample not in sample_names:
            continue
        for dataset, h in datasets.items():
            try:
                h_sel = h[category, "nominal", :]
            except (KeyError, ValueError):
                continue
            v = h_sel.values()
            if values is None:
                values = v.copy()
                edges = h_sel.axes[0].edges
            else:
                values += v
    return values, edges


def plot_stacked(out, var_name, category, xlabel, log_y, xlim, lumi, outdir):
    if var_name not in out["variables"]:
        print(f"    Skipping {var_name} — not in output")
        return

    var_data = out["variables"][var_name]

    all_values = []
    all_edges = None
    labels = []
    colors = []

    for group in SAMPLE_GROUPS:
        values, edges = get_group_values(var_data, group["samples"], category)
        if values is None:
            continue
        all_values.append(values)
        if all_edges is None:
            all_edges = edges
        labels.append(group["label"])
        colors.append(group["color"])

    if not all_values:
        print(f"    No data for {var_name} in {category}")
        return

    fig, ax = plt.subplots()

    hep.histplot(
        all_values,
        bins=all_edges,
        label=labels,
        color=colors,
        stack=True,
        histtype="fill",
        ax=ax,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Events")
    if log_y:
        ax.set_yscale("log")
    if xlim is not None:
        ax.set_xlim(xlim)
    ax.legend(loc="upper right", reverse=True)
    hep.cms.label("Preliminary", data=False, lumi=lumi, ax=ax)

    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{var_name}.png")
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved {outpath}")


def main():
    parser = argparse.ArgumentParser(description="Make stacked MC histograms from coffea output")
    parser.add_argument("-i", "--input", required=True, help="Path to output_all.coffea")
    parser.add_argument("-o", "--outdir", default="plots/stacked_mc", help="Output directory")
    parser.add_argument("-c", "--categories", nargs="+", default=["emu_pre", "emu_cr"],
                        help="Categories to plot")
    parser.add_argument("--lumi", type=float, default=None, help="Luminosity in fb^-1 for label")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    out = load(args.input)

    for category in args.categories:
        cat_outdir = os.path.join(args.outdir, category)
        print(f"\nCategory: {category}")
        for var_name, var_cfg in VARIABLES.items():
            print(f"  Plotting {var_name}...")
            plot_stacked(out, var_name, category, lumi=args.lumi, outdir=cat_outdir, **var_cfg)


if __name__ == "__main__":
    main()
