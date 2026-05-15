import hist

def apply_common_args_to_hist(h, **kwargs):
    xstart = hist.loc(0 if not kwargs["xstart"] else kwargs["xstart"])
    # ystart = hist.loc(0 if not kwargs["ystart"] else kwargs["ystart"])
    return h[xstart:hist.loc(kwargs["xend"])]

def apply_common_args_to_ax(ax, **kwargs):
    if kwargs["xmin"] is not None:
        ax.set_xlim(left=kwargs["xmin"])

    if kwargs["xmax"] is not None:
        ax.set_xlim(right=kwargs["xmax"])

    if kwargs["ymin"] is not None:
        ax.set_ylim(bottom=kwargs["ymin"])

    if kwargs["ymax"] is not None:
        ax.set_ylim(top=kwargs["ymax"])

    if kwargs["xlog"]:
        ax.set_xscale("log")

    if kwargs["ylog"]:
        ax.set_yscale("log")

def add_common_args(parser):
    parser.add_argument("--xmin", type=float, help="Minimum x-axis value")
    parser.add_argument("--xmax", type=float, help="Maximum x-axis value")
    parser.add_argument("--ymin", type=float, help="Minimum y-axis value")
    parser.add_argument("--ymax", type=float, help="Maximum y-axis value")
    parser.add_argument("--ylog", action="store_true", help="Use logarithmic scale for y-axis")
    parser.add_argument("--xlog", action="store_true", help="Use logarithmic scale for x-axis")
    parser.add_argument("--xstart", type=float, help="Starting x-axis value for plot range")
    parser.add_argument("--xend", type=float, help="Ending x-axis value for plot range")
    parser.add_argument("--ystart", type=float, help="Starting y-axis value for plot range")
    parser.add_argument("--yend", type=float, help="Ending y-axis value for plot range")


def extract_year(year_key):
    return year_key.split("_")[1]


def get_variables(f):
    return list(f["variables"].keys())


def get_samples(f, variable):
    return list(f["variables"][variable].keys())


def get_years(f, variable, sample):
    return list(set(extract_year(y) for y in f["variables"][variable][sample]))


def get_categories(f, variable, sample, year_key):
    ax = f["variables"][variable][sample][year_key].axes[0]
    return [ax.value(i) for i in range(ax.extent - 1)]


def get_datasets(f, variable, sample, years):
    return [key for year in years
                for key in f["variables"][variable][sample].keys()
            if year in key]


def get_combined_hist(f, variable, samples, datasets, category, is_data):
    if is_data:
        all_hists = [f["variables"][variable][s][d][category, ...] for s in samples for d in datasets]
    else:
        all_hists = [f["variables"][variable][s][d][category, "nominal", ...] for s in samples for d in datasets]

    return sum(all_hists)


def get_is_data(f, dataset):
    return f["datasets_metadata"]["by_dataset"][dataset]["isMC"] == "False"
