import sys
import argparse
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from poca import calculate

# Map TTree branch suffix to the field name poca.calculate expects
BRANCH_TO_FIELD = {
    "phi":      "track_phi",
    "lambda":   "track_lambda",
    "pt":       "pt",
    "charge":   "charge",
    "bField_z": "bField_z",
    "vx":       "track_vx",
    "vy":       "track_vy",
    "vz":       "track_vz",
}

def point_distance(p, q):
    dx = p["x"] - q["x"]
    dy = p["y"] - q["y"]
    dz = p["z"] - q["z"]
    return np.sqrt(dx**2 + dy**2 + dz**2)

def make_collection(raw, prefix):
    return ak.zip({field: raw[f"{prefix}_{branch}"]
                   for branch, field in BRANCH_TO_FIELD.items()})

def main():
    parser = argparse.ArgumentParser(description="Compare Python vs C++ POCA")
    parser.add_argument("input", help="ROOT file from LeptonPocaAnalyzer")
    args = parser.parse_args()

    with uproot.open(args.input) as f:
        raw = f["leptonPoca/LeptonPoca"].arrays(library="ak", entry_stop=1000)

    l1 = make_collection(raw, "trk1")
    l2 = make_collection(raw, "trk2")

    py_p1, py_p2 = calculate(l1, l2)

    cpp_valid = raw["poca_status"] == 0
    cpp_p1 = ak.mask(ak.zip({"x": raw["poca1_x"], "y": raw["poca1_y"], "z": raw["poca1_z"]}), cpp_valid)
    cpp_p2 = ak.mask(ak.zip({"x": raw["poca2_x"], "y": raw["poca2_y"], "z": raw["poca2_z"]}), cpp_valid)

    py_valid = ~ak.is_none(py_p1)
    n = len(py_valid)
    both_valid = py_valid & cpp_valid
    py_only    = py_valid & ~cpp_valid
    cpp_only   = ~py_valid & cpp_valid
    neither    = ~py_valid & ~cpp_valid

    print(f"\nValidity comparison (n={n}):")
    print(f"  both valid:   {ak.sum(both_valid)}")
    print(f"  python only:  {ak.sum(py_only)}")
    print(f"  cpp only:     {ak.sum(cpp_only)}")
    print(f"  neither:      {ak.sum(neither)}")

    diff1 = ak.to_numpy(ak.drop_none(point_distance(py_p1, cpp_p1)))
    diff2 = ak.to_numpy(ak.drop_none(point_distance(py_p2, cpp_p2)))

    for label, diff in [("trk1 POCA", diff1), ("trk2 POCA", diff2)]:
        print(f"\n{label} |py - cpp| [cm]:  n={len(diff)}")
        print(f"  mean = {diff.mean():.3e}")
        print(f"  max  = {diff.max():.3e}")
        print(f"  > 1 um: {(diff > 1e-4).sum()}")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, label, diff in [
        (axes[0], "trk1 POCA", diff1),
        (axes[1], "trk2 POCA", diff2),
    ]:
        ax.hist(diff, bins=100)
        ax.set_xlabel("|py - cpp| [cm]")
        ax.set_title(label)
        ax.set_yscale("log")
    fig.tight_layout()
    plt.savefig("poca_diff.png", dpi=150)
    print("\nSaved poca_diff.png")

if __name__ == "__main__":
    main()
