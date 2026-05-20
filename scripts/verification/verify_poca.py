import sys
import argparse
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from poca_phi  import calculate as calculate_phi
from poca_pxpy import calculate as calculate_pxpy

# track_phi/lambda from TTree (float32); vx/vy/vz/bField_z float32
BRANCH_TO_FIELD_PHI = {
    "phi":      "track_phi",
    "lambda":   "track_lambda",
    "pt":       "pt",
    "charge":   "charge",
    "bField_z": "bField_z",
    "vx":       "track_vx",
    "vy":       "track_vy",
    "vz":       "track_vz",
}

# px/py/pz as float32; vx/vy/vz/bField_z float32
BRANCH_TO_FIELD_PXPY_F32 = {
    "px_f":     "px",
    "py_f":     "py",
    "pz_f":     "pz",
    "charge":   "charge",
    "bField_z": "bField_z",
    "vx":       "track_vx",
    "vy":       "track_vy",
    "vz":       "track_vz",
}

# px/py/pz as float64; vx/vy/vz/bField_z float64
BRANCH_TO_FIELD_PXPY_F64 = {
    "px":         "px",
    "py":         "py",
    "pz":         "pz",
    "charge":     "charge",
    "bField_z_d": "bField_z",
    "vx_d":       "track_vx",
    "vy_d":       "track_vy",
    "vz_d":       "track_vz",
}

def point_distance(p, q):
    dx = p["x"] - q["x"]
    dy = p["y"] - q["y"]
    dz = p["z"] - q["z"]
    return np.sqrt(dx**2 + dy**2 + dz**2)

def midpoint(p1, p2):
    return ak.zip({
        "x": (p1["x"] + p2["x"]) / 2,
        "y": (p1["y"] + p2["y"]) / 2,
        "z": (p1["z"] + p2["z"]) / 2,
    })

def print_stats(label, diff):
    arr = ak.to_numpy(ak.drop_none(diff))
    print(f"  {label}: n={len(arr)}  mean={arr.mean():.3e}  max={arr.max():.3e}  >1um={(arr > 1e-4).sum()}")

def make_collection(raw, prefix, field_map):
    return ak.zip({field: raw[f"{prefix}_{branch}"]
                   for branch, field in field_map.items()})

def run_comparison(label, calculate_fn, l1, l2, cpp_p1, cpp_p2, cpp_mid):
    py_p1, py_p2 = calculate_fn(l1, l2)
    py_mid = midpoint(py_p1, py_p2)

    py_valid  = ~ak.is_none(py_p1)
    cpp_valid = ~ak.is_none(cpp_p1)

    print(f"\n=== {label} ===")
    print(f"  both valid: {ak.sum(py_valid & cpp_valid)}  "
          f"py-only: {ak.sum(py_valid & ~cpp_valid)}  "
          f"cpp-only: {ak.sum(~py_valid & cpp_valid)}  "
          f"neither: {ak.sum(~py_valid & ~cpp_valid)}")
    print("  Individual POCA points:")
    print_stats("trk1 POCA", point_distance(py_p1, cpp_p1))
    print_stats("trk2 POCA", point_distance(py_p2, cpp_p2))
    print("  Midpoint:")
    print_stats("midpoint ", point_distance(py_mid, cpp_mid))

    return py_p1, py_p2, py_mid

def main():
    parser = argparse.ArgumentParser(description="Compare Python vs C++ POCA")
    parser.add_argument("input", help="ROOT file from LeptonPocaAnalyzer")
    args = parser.parse_args()

    with uproot.open(args.input) as f:
        raw = f["leptonPoca/LeptonPoca"].arrays(library="ak", entry_stop=1000)

    cpp_valid = raw["poca_status"] == 0
    cpp_p1  = ak.mask(ak.zip({"x": raw["poca1_x"], "y": raw["poca1_y"], "z": raw["poca1_z"]}), cpp_valid)
    cpp_p2  = ak.mask(ak.zip({"x": raw["poca2_x"], "y": raw["poca2_y"], "z": raw["poca2_z"]}), cpp_valid)
    cpp_mid = midpoint(cpp_p1, cpp_p2)

    l1_phi      = make_collection(raw, "trk1", BRANCH_TO_FIELD_PHI)
    l2_phi      = make_collection(raw, "trk2", BRANCH_TO_FIELD_PHI)
    l1_pxpy_f32 = make_collection(raw, "trk1", BRANCH_TO_FIELD_PXPY_F32)
    l2_pxpy_f32 = make_collection(raw, "trk2", BRANCH_TO_FIELD_PXPY_F32)
    l1_pxpy_f64 = make_collection(raw, "trk1", BRANCH_TO_FIELD_PXPY_F64)
    l2_pxpy_f64 = make_collection(raw, "trk2", BRANCH_TO_FIELD_PXPY_F64)

    py_p1_phi, py_p2_phi, py_mid_phi = run_comparison(
        "phi (f32 track_phi/lambda)", calculate_phi, l1_phi, l2_phi, cpp_p1, cpp_p2, cpp_mid)
    py_p1_f32, py_p2_f32, py_mid_f32 = run_comparison(
        "px/py f32", calculate_pxpy, l1_pxpy_f32, l2_pxpy_f32, cpp_p1, cpp_p2, cpp_mid)
    py_p1_f64, py_p2_f64, py_mid_f64 = run_comparison(
        "px/py f64", calculate_pxpy, l1_pxpy_f64, l2_pxpy_f64, cpp_p1, cpp_p2, cpp_mid)

    # 3x3 histogram: rows = approach, cols = trk1 / trk2 / midpoint
    fig, axes = plt.subplots(3, 3, figsize=(14, 10))
    comparisons = [
        ("phi  trk1",  ak.to_numpy(ak.drop_none(point_distance(py_p1_phi, cpp_p1)))),
        ("phi  trk2",  ak.to_numpy(ak.drop_none(point_distance(py_p2_phi, cpp_p2)))),
        ("phi  midpt", ak.to_numpy(ak.drop_none(point_distance(py_mid_phi, cpp_mid)))),
        ("f32  trk1",  ak.to_numpy(ak.drop_none(point_distance(py_p1_f32, cpp_p1)))),
        ("f32  trk2",  ak.to_numpy(ak.drop_none(point_distance(py_p2_f32, cpp_p2)))),
        ("f32  midpt", ak.to_numpy(ak.drop_none(point_distance(py_mid_f32, cpp_mid)))),
        ("f64  trk1",  ak.to_numpy(ak.drop_none(point_distance(py_p1_f64, cpp_p1)))),
        ("f64  trk2",  ak.to_numpy(ak.drop_none(point_distance(py_p2_f64, cpp_p2)))),
        ("f64  midpt", ak.to_numpy(ak.drop_none(point_distance(py_mid_f64, cpp_mid)))),
    ]
    for ax, (label, diff) in zip(axes.flat, comparisons):
        ax.hist(diff, bins=100)
        ax.set_xlabel("|py - cpp| [cm]")
        ax.set_title(label)
        ax.set_yscale("log")
    fig.tight_layout()
    plt.savefig("poca_diff.png", dpi=150)
    print("\nSaved poca_diff.png")

if __name__ == "__main__":
    main()
