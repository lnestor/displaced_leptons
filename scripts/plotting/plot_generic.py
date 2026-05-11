import argparse
import coffea.util
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

def plot(root, output, variable, sample, year, category, is_data, **kwargs):
    fix, ax = plt.subplots()
    hep.cms.label("Preliminary", ax=ax, data=is_data, loc=1) # loc=1 is top left interior

    if is_data:
        hist = root["variables"][variable][sample][year][category, :]
    else:
        hist = root["variables"][variable][sample][year][category, "nominal", :]

    import pdb; pdb.set_trace()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to .coffea file")
    parser.add_argument("-o", "--output", help="Output filename. Defaults to <DEFUALT")
    parser.add_argument("-v", "--variable", required=True)
    parser.add_argument("-c", "--category")
    parser.add_argument("-y", "--year")
    parser.add_argument("-s", "--sample")
    parser.add_argument("-n", "--normalize", action="store_true")
    parser.add_argument("-ps", "--plot-separately", action="store_true")
    parser.add_argument("--xmin", type=float, default=None)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=None)
    parser.add_argument("--ymax", type=float, default=None)
    parser.add_argument("--xlog", action="store_true")
    parser.add_argument("--ylog", action="store_true")
    args = parser.parse_args()

    print(f"Loading {args.input}")
    f = coffea.util.load(args.input)

    valid_vars = f["variables"].keys()
    if args.variable not in valid_vars:
        parser.error(f"Unknown variable: {args.variable}. Choose from {', '.join(valid_vars)}")

    """
    samples = valid_samples = f["variables"][args.variable].keys()
    if args.sample is None:
        print(f"Sample not provided. Using all: {', '.join(valid_samples)}")
    else:
        if args.sample not in valid_samples:
            parser.error(f"Unknown sample: {args.sample}. Choose from {', '.join(valid_samples)}")
        else:
            print(f"Using sample {args.sample}")
            samples = [args.sample]

    # For now: assume all years are present on all samples
    years = valid_years = f["variables"][args.variable][samples[0]].keys()
    if args.year is None:
        print(f"Year not provided. Using all: {', '.join(valid_years)}")
    else:
        if args.year not in valid_years:
            parser.error(f"Unknown year: {args.year}. Choose from {', '.join(valid_years)}")
        else:
            print(f"Using year {args.year}")
            years = [args.year]
    """

    # Validate categories

    plot(
        f,
        args.output,
        args.variable,
        args.sample,
        args.year,
        args.category,
        True,
        normalize=args.normalize,
        xlim=(args.xmin, args.xmax),
        ylim=(args.ymin, args.ymax),
        xlog=args.xlog,
        ylog=args.ylog
    )


if __name__ == "__main__":
    main()
