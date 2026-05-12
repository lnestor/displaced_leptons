def apply_common_args(ax, **kwargs):
    if kwargs["xlim"][0] is not None:
        ax.set_xlim(left=kwargs["xlim"][0])

    if kwargs["xlim"][1] is not None:
        ax.set_xlim(right=kwargs["xlim"][1])

    if kwargs["ylim"][0] is not None:
        ax.set_ylim(bottom=kwargs["ylim"][0])

    if kwargs["ylim"][1] is not None:
        ax.set_ylim(top=kwargs["ylim"][1])

    if kwargs["xlog"]:
        ax.set_xscale("log")

    if kwargs["ylog"]:
        ax.set_yscale("log")

def add_common_args(parser):
    parser.add_argument("--xmin", type=float, default=None, help="Minimum x-axis value")
    parser.add_argument("--xmax", type=float, default=None, help="Maximum x-axis value")
    parser.add_argument("--ymin", type=float, default=None, help="Minimum y-axis value")
    parser.add_argument("--ymax", type=float, default=None, help="Maximum y-axis value")
    parser.add_argument("--ylog", action="store_true", help="Use logarithmic scale for y-axis")
    parser.add_argument("--xlog", action="store_true", help="Use logarithmic scale for x-axis")
    parser.add_argument("--xstart", type=float, default=None, help="Starting x-axis value for plot range")
    parser.add_argument("--xend", type=float, default=None, help="Ending x-axis value for plot range")
    parser.add_argument("--ystart", type=float, default=None, help="Starting y-axis value for plot range")
    parser.add_argument("--yend", type=float, default=None, help="Ending y-axis value for plot range")


