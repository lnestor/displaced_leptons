import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from coffea.util import load

hep.style.use("CMS")

ETA_RANGE = 4.0
D0_RANGE = 2000

# Optional label/color overrides for known samples; unknown samples fall back to name + color cycle
LABELS = {
    "DisplacedSUSY_stopToLBottom_M_200_1mm_TuneCP5_13TeV-madgraph-pythia8":  r"$\tilde{t}\to lb$, M=200 GeV, c$\tau$=1mm",
    "DisplacedSUSY_stopToLBottom_M_1000_1mm_TuneCP5_13TeV-madgraph-pythia8": r"$\tilde{t}\to lb$, M=1000 GeV, c$\tau$=1mm",
    "DisplacedSUSY_stopToLBottom_M_1800_1mm_TuneCP5_13TeV-madgraph-pythia8": r"$\tilde{t}\to lb$, M=1800 GeV, c$\tau$=1mm",
    "DisplacedSUSY_stopToLD_M_200_1mm_TuneCP5_13TeV-madgraph-pythia8":       r"$\tilde{t}\to ld$, M=200 GeV, c$\tau$=1mm",
    "DisplacedSUSY_stopToLD_M_1000_1mm_TuneCP5_13TeV-madgraph-pythia8":      r"$\tilde{t}\to ld$, M=1000 GeV, c$\tau$=1mm",
    "DisplacedSUSY_stopToLD_M_1800_1mm_TuneCP5_13TeV-madgraph-pythia8":      r"$\tilde{t}\to ld$, M=1800 GeV, c$\tau$=1mm",
}

COLORS = {
    "DisplacedSUSY_stopToLBottom_M_200_1mm_TuneCP5_13TeV-madgraph-pythia8":  "black",
    "DisplacedSUSY_stopToLBottom_M_1000_1mm_TuneCP5_13TeV-madgraph-pythia8": "red",
    "DisplacedSUSY_stopToLBottom_M_1800_1mm_TuneCP5_13TeV-madgraph-pythia8": "blue",
    "DisplacedSUSY_stopToLD_M_200_1mm_TuneCP5_13TeV-madgraph-pythia8":       "green",
    "DisplacedSUSY_stopToLD_M_1000_1mm_TuneCP5_13TeV-madgraph-pythia8":      "purple",
    "DisplacedSUSY_stopToLD_M_1800_1mm_TuneCP5_13TeV-madgraph-pythia8":      "teal",
}

# Variable metadata: axis label, y-axis limit, x-axis limit (None = auto), log y-axis
VARIABLES = {
    "Electron_pt":  (r"Electron $p_T$ [GeV]",       (0, 0.1),    None,                    False),
    "Electron_eta": (r"Electron $\eta$",             (0, 0.1),    (-ETA_RANGE, ETA_RANGE), False),
    "Electron_d0":  (r"Electron $|d_0|$ [$\mu$m]",  (1e-4, 1),   (0, D0_RANGE),           True),
    "Muon_pt":      (r"Muon $p_T$ [GeV]",           (0, 0.1),    None,                    False),
    "Muon_eta":     (r"Muon $\eta$",                 (0, 0.1),    (-ETA_RANGE, ETA_RANGE), False),
    "Muon_d0":      (r"Muon $|d_0|$ [$\mu$m]",      (1e-4, 1),   (0, D0_RANGE),           True),
}


def _make_step(edges, values, xlim):
    plot_edges = np.array(edges)
    plot_values = np.array(values)
    if xlim is not None:
        if plot_edges[0] > xlim[0]:
            plot_edges = np.concatenate([[xlim[0]], plot_edges])
            plot_values = np.concatenate([[0], plot_values])
        if plot_edges[-1] < xlim[1]:
            plot_edges = np.concatenate([plot_edges, [xlim[1]]])
            plot_values = np.concatenate([plot_values, [0]])
    x_step = np.repeat(plot_edges, 2)[1:-1]
    y_step = np.repeat(plot_values, 2)
    return x_step, y_step


def plot_variable(out, var_name, category, year, xlabel, ylim, xlim, log_y, outdir, normalize, combine):
    if var_name not in out["variables"]:
        print(f"  Skipping {var_name} — not in output")
        return

    fig, ax = plt.subplots()
    var = out["variables"][var_name]

    if combine:
        for sample, datasets in var.items():
            label = LABELS.get(sample, sample)
            color = COLORS.get(sample)

            combined_values = None
            combined_edges = None
            for dataset, h in datasets.items():
                if year not in dataset:
                    continue
                h_sel = h[category, "nominal", :]
                values = h_sel.values()
                edges = h_sel.axes[0].edges
                if combined_values is None:
                    combined_values = np.array(values, dtype=float)
                    combined_edges = np.array(edges)
                else:
                    combined_values += values

            if combined_values is None or combined_values.sum() == 0:
                continue
            if normalize:
                combined_values /= combined_values.sum()

            x_step, y_step = _make_step(combined_edges, combined_values, xlim)
            ax.plot(x_step, y_step, label=label, color=color)
    else:
        for sample, datasets in var.items():
            for dataset, h in datasets.items():
                if year not in dataset:
                    continue
                h_sel = h[category, "nominal", :]
                values = np.array(h_sel.values(), dtype=float)
                edges = h_sel.axes[0].edges

                if values.sum() == 0:
                    continue
                if normalize:
                    values /= values.sum()

                x_step, y_step = _make_step(edges, values, xlim)
                ax.plot(x_step, y_step, label=dataset)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Entries (Unit Area Norm.)" if normalize else "Entries")
    ax.margins(x=0)
    if log_y:
        ax.set_yscale("log")
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.legend(fontsize=7)
    hep.cms.label("Preliminary Simulation", data=False, ax=ax)

    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{var_name}_{year}_{category}.png")
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {outpath}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",     required=True,        help="Path to output_all.coffea")
    parser.add_argument("-o", "--outdir",    default="plots/kinematics", help="Output directory")
    parser.add_argument("--category",        default="emu",        help="Category to plot")
    parser.add_argument("--year",            default="2017",       help="Year string to filter datasets")
    parser.add_argument("--normalize",       action="store_true",  help="Normalize each histogram to unit area")
    parser.add_argument("--combine",         action="store_true",  help="Sum all datasets within a sample into one line")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    out = load(args.input)

    for var_name, (xlabel, ylim, xlim, log_y) in VARIABLES.items():
        print(f"Plotting {var_name}...")
        plot_variable(
            out, var_name, args.category, args.year,
            xlabel, ylim, xlim, log_y, args.outdir,
            normalize=args.normalize,
            combine=args.combine,
        )


if __name__ == "__main__":
    main()
