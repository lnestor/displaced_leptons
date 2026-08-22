from typing import List, Tuple

from coffea.processor import set_accumulator
from coffea.processor.executor import Runner as CoffeaRunner
from coffea.processor.executor import UprootMissTreeError
from coffea.util import _exception_chain


def _build_automatic_retries():
    def automatic_retries(retries: int, skipbadfiles: bool, func, *args, **kwargs):
        import warnings

        def _skip_result(exc):
            wrapped = getattr(func, "func", func)
            if getattr(wrapped, "__name__", None) == "metadata_fetcher":
                return None
            item = args[0]
            if isinstance(item, tuple):  # when heavy_input is set
                item = item[0]
            return {
                "skipped_files": set_accumulator(
                    [(item.dataset, item.filename, str(exc))]
                )
            }

        retry_count = 0
        while retry_count <= retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                chain = _exception_chain(e)
                if skipbadfiles and any(
                    isinstance(c, (OSError, UprootMissTreeError)) for c in chain
                ):
                    warnings.warn(str(e))
                    return _skip_result(e)
                if (
                    skipbadfiles
                    and (retries == retry_count)
                    and any(
                        s in str(c)
                        for c in chain
                        for s in [
                            "Invalid redirect URL",
                            "Operation expired",
                            "Socket timeout",
                        ]
                    )
                ):
                    warnings.warn(str(e))
                    return _skip_result(e)
                if (
                    not skipbadfiles
                    or any("Auth failed" in str(c) for c in chain)
                    or retries == retry_count
                ):
                    raise e
                warnings.warn("Attempt %d of %d." % (retry_count + 1, retries + 1))
            retry_count += 1

    return automatic_retries


class Runner(CoffeaRunner):
    """coffea Runner that records files skipped via skipbadfiles.

    Coffea's own skipbadfiles handling only does a warnings.warn() when a
    file is skipped -- nothing is returned or stored anywhere retrievable.
    Instead of returning None for a skipped chunk (coffea's default) or
    routing around it via a distributed Queue, automatic_retries returns a
    dict with a "skipped_files" key. That rides through the same
    accumulate()-based map-reduce tree that already merges every chunk's
    "out"/"metrics"/"processed" back to the client, so it needs no separate
    channel. run() then pulls it out of the merged result into
    self.failed_files.

    automatic_retries is built as a closure (_build_automatic_retries)
    rather than a plain method: distributed's pickler only calls cloudpickle
    (which respects cloudpickle.register_pickle_by_value) when plain pickle
    fails on the functools.partial coffea wraps this in -- a closure is the
    one thing plain pickle can't handle by reference, which is what actually
    gets this shipped to workers instead of them trying to import lib.
    """

    def __post_init__(self):
        super().__post_init__()
        self.failed_files: List[Tuple[str, str, str]] = []

    def run(self, fileset, processor_instance, treename=None):
        result = super().run(fileset, processor_instance, treename)
        self.failed_files = sorted(result.pop("skipped_files", set_accumulator()))
        return result

    automatic_retries = staticmethod(_build_automatic_retries())
