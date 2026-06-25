"""
Decode vidNestedWPBitmap for Event B to identify which tight ID cut(s) fail.

Event B: run=319656, lumi=124, event=96217529
  PC fails Stage06_EleID (cutBased=3, medium not tight)
  CMSSW passes all cuts through Stage17

The bitmap stores 3 bits per cut encoding the highest WP that cut passes:
  0=fail all, 1=pass veto, 2=pass loose, 3=pass medium, 4=pass tight

Usage: python diag_eventB_vid.py <nano_file>
"""

import sys
import uproot

EVENT_B = (319656, 124, 96217529)

CUT_NAMES = [
    "MinPtCut",
    "GsfEleSCEtaMultiRangeCut",
    "GsfEleDEtaInSeedCut",
    "GsfEleDPhiInCut",
    "GsfEleFull5x5SigmaIEtaIEtaCut",
    "GsfEleHadronicOverEMEnergyScaledCut",
    "GsfEleEInverseMinusPInverseCut",
    "GsfEleRelPFIsoScaledCut",          # isolation -- cut index 7
    "GsfEleConversionVetoCut",
    "GsfEleMissingHitsCut",
]
WP_LABELS = {0: "FAIL", 1: "veto", 2: "loose", 3: "medium", 4: "tight"}
ISO_CUT = 7


def decode_bitmap(bitmap):
    return [(bitmap >> (3 * i)) & 0x7 for i in range(len(CUT_NAMES))]


def main():
    if len(sys.argv) != 2:
        print("Usage: python diag_eventB_vid.py <nano_file>")
        sys.exit(1)

    nano = uproot.open(sys.argv[1])["Events"]
    arrays = nano.arrays(
        ["run", "luminosityBlock", "event",
         "Electron_pt", "Electron_eta", "Electron_deltaEtaSC",
         "Electron_cutBased", "Electron_vidNestedWPBitmap"],
        library="np"
    )

    for i in range(len(arrays["run"])):
        ev = (int(arrays["run"][i]),
              int(arrays["luminosityBlock"][i]),
              int(arrays["event"][i]))
        if ev != EVENT_B:
            continue

        print(f"\nEvent B  run={ev[0]}  lumi={ev[1]}  event={ev[2]}")
        n_ele = len(arrays["Electron_pt"][i])
        print(f"{n_ele} electron(s) in NanoAOD\n")

        for j in range(n_ele):
            pt        = float(arrays["Electron_pt"][i][j])
            eta       = float(arrays["Electron_eta"][i][j])
            dEtaSC    = float(arrays["Electron_deltaEtaSC"][i][j])
            etaSC     = abs(eta + dEtaSC)
            cutBased  = int(arrays["Electron_cutBased"][i][j])
            bitmap    = int(arrays["Electron_vidNestedWPBitmap"][i][j])
            cuts      = decode_bitmap(bitmap)

            passes_tight_no_iso = all(
                cuts[k] >= 4 for k in range(len(CUT_NAMES)) if k != ISO_CUT
            )

            print(f"  Electron {j}:  pt={pt:.3f}  eta={eta:.4f}  etaSC={etaSC:.4f}"
                  f"  cutBased={cutBased}  bitmap=0x{bitmap:08x}")
            print(f"  {'Cut':<40}  {'value':>5}  {'WP':>6}  {'passes tight':>12}")
            print(f"  {'-'*68}")
            for k, name in enumerate(CUT_NAMES):
                v = cuts[k]
                label = WP_LABELS.get(v, str(v))
                iso_tag = "  <- ISOLATION" if k == ISO_CUT else ""
                passes = "YES" if v >= 4 else "NO"
                print(f"  {name:<40}  {v:>5}  {label:>6}  {passes:>12}{iso_tag}")
            print(f"\n  tight_no_iso (all cuts >= tight except isolation): {passes_tight_no_iso}")
            print(f"  cutBased (standard, includes isolation):            {cutBased} "
                  f"({'tight' if cutBased >= 4 else 'medium' if cutBased == 3 else str(cutBased)})")
        return

    print(f"Event B not found in {sys.argv[1]}")


if __name__ == "__main__":
    main()
