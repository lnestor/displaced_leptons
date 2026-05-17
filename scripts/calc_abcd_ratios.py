import argparse
from coffea_file import CoffeaFile
import hist

_CONFIGS = [
    {
        "channel": "emu",
        "hist_name": "abcd_emu",
        "sample": "MuonEG"
    },
    {
        "channel": "ee",
        "hist_name": "abcd_ee",
        "sample": "DoubleElectron"
    },
    {
        "channel": "mumu",
        "hist_name": "abcd_mumu",
        "sample": "DoubleMuon"
    },
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--channel", choices=["ee", "mumu", "emu"])
    parser.add_argument("--years", nargs="+")
    args = parser.parse_args()

    f = CoffeaFile(args.input)
    hist_name = f"abcd_{args.channel}"
    samples = f.get_samples(hist_name)

    h = f.get_total_hist(hist_name, category=args.channel, years=args.years)
    h_no_pt = h.project("e1_d0", "mu1_d0")


    # SR1 Low pt
    # SR1 High pt
    # SR2

    loc_0_100 = slice(hist.loc(0), hist.loc(100))
    loc_100_500 = slice(hist.loc(100), hist.loc(500))
    loc_500_10cm = slice(hist.loc(500), hist.loc(1e5))

    loc_low_pt = slice(hist.loc(0), hist.loc(140))
    loc_high_pt = slice(hist.loc(140), None)

    a_no_pt = h_no_pt[loc_0_100, loc_0_100].sum().value
    a_low_pt = h[loc_0_100, loc_0_100, loc_low_pt].sum().value
    a_high_pt = h[loc_0_100, loc_0_100, loc_high_pt].sum().value

    sr1_low_pt_b = h[loc_0_100, loc_100_500, loc_low_pt].sum().value
    sr1_high_pt_b = h[loc_0_100, loc_100_500, loc_high_pt].sum().value
    sr1_low_pt_c = h[loc_100_500, loc_0_100, loc_low_pt].sum().value
    sr1_high_pt_c = h[loc_100_500, loc_0_100, loc_high_pt].sum().value
    sr1_low_pt_d = h[loc_100_500, loc_100_500, loc_low_pt].sum().value
    sr1_high_pt_d = h[loc_100_500, loc_100_500, loc_high_pt].sum().value

    sr2_b = h_no_pt[loc_0_100, loc_100_500].sum().value
    sr2_c = h_no_pt[loc_500_10cm, loc_0_100].sum().value
    sr2_d = h_no_pt[loc_500_10cm, loc_100_500].sum().value

    sr3_b = h_no_pt[loc_0_100, loc_500_10cm].sum().value
    sr3_c = h_no_pt[loc_100_500, loc_0_100].sum().value
    sr3_d = h_no_pt[loc_100_500, loc_500_10cm].sum().value

    sr4_b = h_no_pt[loc_0_100, loc_500_10cm].sum().value
    sr4_c = h_no_pt[loc_500_10cm, loc_0_100].sum().value
    sr4_d = h_no_pt[loc_500_10cm, loc_500_10cm].sum().value

    # Print ABCD results
    print("\n" + "="*60)
    print("SR1 Low pT (100-500 µm closure test)")
    print("="*60)
    print(f"A (0-100, 0-100):     {a_low_pt:.2f}")
    print(f"B (0-100, 100-500):   {sr1_low_pt_b:.2f}")
    print(f"C (100-500, 0-100):   {sr1_low_pt_c:.2f}")
    print(f"D (100-500, 100-500): {sr1_low_pt_d:.2f} (observed)")
    sr1_low_pt_pred = (sr1_low_pt_b * sr1_low_pt_c) / a_low_pt if a_low_pt > 0 else 0
    print(f"D predicted:          {sr1_low_pt_pred:.2f}")
    sr1_low_pt_ratio = sr1_low_pt_d / sr1_low_pt_pred if sr1_low_pt_pred > 0 else 0
    print(f"Ratio (obs/pred):     {sr1_low_pt_ratio:.3f}")

    print("\n" + "="*60)
    print("SR1 High pT (100-500 µm closure test)")
    print("="*60)
    print(f"A (0-100, 0-100):     {a_high_pt:.2f}")
    print(f"B (0-100, 100-500):   {sr1_high_pt_b:.2f}")
    print(f"C (100-500, 0-100):   {sr1_high_pt_c:.2f}")
    print(f"D (100-500, 100-500): {sr1_high_pt_d:.2f} (observed)")
    sr1_high_pt_pred = (sr1_high_pt_b * sr1_high_pt_c) / a_high_pt if a_high_pt > 0 else 0
    print(f"D predicted:          {sr1_high_pt_pred:.2f}")
    sr1_high_pt_ratio = sr1_high_pt_d / sr1_high_pt_pred if sr1_high_pt_pred > 0 else 0
    print(f"Ratio (obs/pred):     {sr1_high_pt_ratio:.3f}")

    print("\n" + "="*60)
    print("SR2 (500 µm - 10 cm signal region)")
    print("="*60)
    print(f"A (0-100, 0-100):       {a_no_pt:.2f}")
    print(f"B (0-100, 100-500):     {sr2_b:.2f}")
    print(f"C (500-10cm, 0-100):    {sr2_c:.2f}")
    print(f"D (500-10cm, 100-500):  {sr2_d:.2f} (observed)")
    sr2_pred = (sr2_b * sr2_c) / a_no_pt if a_no_pt > 0 else 0
    print(f"D predicted:            {sr2_pred:.2f}")
    sr2_ratio = sr2_d / sr2_pred if sr2_pred > 0 else 0
    print(f"Ratio (obs/pred):       {sr2_ratio:.3f}")

    print("\n" + "="*60)
    print("SR3 (100-500 µm vs 500 µm-10 cm)")
    print("="*60)
    print(f"A (0-100, 0-100):       {a_no_pt:.2f}")
    print(f"B (0-100, 500-10cm):    {sr3_b:.2f}")
    print(f"C (100-500, 0-100):     {sr3_c:.2f}")
    print(f"D (100-500, 500-10cm):  {sr3_d:.2f} (observed)")
    sr3_pred = (sr3_b * sr3_c) / a_no_pt if a_no_pt > 0 else 0
    print(f"D predicted:            {sr3_pred:.2f}")
    sr3_ratio = sr3_d / sr3_pred if sr3_pred > 0 else 0
    print(f"Ratio (obs/pred):       {sr3_ratio:.3f}")

    print("\n" + "="*60)
    print("SR4 (500 µm-10 cm inclusive signal region)")
    print("="*60)
    print(f"A (0-100, 0-100):       {a_no_pt:.2f}")
    print(f"B (0-100, 500-10cm):    {sr4_b:.2f}")
    print(f"C (500-10cm, 0-100):    {sr4_c:.2f}")
    print(f"D (500-10cm, 500-10cm): {sr4_d:.2f} (observed)")
    sr4_pred = (sr4_b * sr4_c) / a_no_pt if a_no_pt > 0 else 0
    print(f"D predicted:            {sr4_pred:.2f}")
    sr4_ratio = sr4_d / sr4_pred if sr4_pred > 0 else 0
    print(f"Ratio (obs/pred):       {sr4_ratio:.3f}")
    print("="*60 + "\n")



if __name__ == "__main__":
    main()
