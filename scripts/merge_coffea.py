import argparse
import glob
import os

from coffea.util import load, save
from coffea.processor import accumulate


def main():
    parser = argparse.ArgumentParser(
        description="Accumulate coffea output files without applying postprocessing."
                    " Use this to merge outputs from --process-separately runs."
    )
    parser.add_argument("input", nargs="+", help="Input .coffea files (glob patterns accepted)")
    parser.add_argument("-o", "--output", required=True, help="Output .coffea file")
    args = parser.parse_args()

    output_path = os.path.realpath(args.output)

    inputfiles = []
    for pattern in args.input:
        expanded = [os.path.realpath(f) for f in glob.glob(pattern)]
        if not expanded:
            print(f"Warning: no files matched '{pattern}'")
        inputfiles.extend(expanded)
    inputfiles = sorted(set(inputfiles))

    if output_path in inputfiles:
        print("Note: target output file is included in input files. It will not be included in the merge.")
        inputfiles.remove(output_path)

    if not inputfiles:
        print("Error: no input files found")
        return

    print(f"Merging {len(inputfiles)} files:")
    for f in inputfiles:
        print(f"  {f}")

    out = accumulate([load(f) for f in inputfiles])
    save(out, args.output)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
