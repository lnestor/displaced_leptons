from functools import partial
from typing import Dict, List, Tuple

from coffea.processor import (
    DaskExecutor,
    FuturesExecutor,
    ParslExecutor,
    set_accumulator,
)
from coffea.processor.executor import Runner as CoffeaRunner
from coffea.processor.executor import UprootMissTreeError
from coffea.util import _exception_chain


def _fetch_populated_metadata(xrootdtimeout, align_clusters, item):
    """Wrap CoffeaRunner.metadata_fetcher's result (a bare set_accumulator of
    FileMeta) in a plain dict, so a failure on this same item (see
    _skip_result, which also returns a plain dict) can be recorded under a
    "skipped_files" key without a type mismatch when the two get merged.
    coffea's accumulate()/iadd() merge MutableMappings generically -- it
    doesn't require dict_accumulator specifically, and in fact requires
    exact type agreement between merged results, so this must match
    _skip_result's plain dict rather than use dict_accumulator."""
    populated = CoffeaRunner.metadata_fetcher(xrootdtimeout, align_clusters, item)
    return {"populated": populated}


def _build_automatic_retries():
    def automatic_retries(retries: int, skipbadfiles: bool, func, *args, **kwargs):
        import traceback
        import warnings

        def _skip_result(exc):
            item = args[0]
            if isinstance(item, tuple):  # when heavy_input is set
                item = item[0]
            return {
                "skipped_files": set_accumulator(
                    [(item.dataset, item.filename, traceback.format_exc())]
                )
            }

        retry_count = 0
        while retry_count <= retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                chain = _exception_chain(e)
                if (
                    skipbadfiles
                    and (retries == retry_count)
                    and any(
                        isinstance(c, (OSError, UprootMissTreeError)) for c in chain
                    )
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

    This also covers files that fail at the preprocessing stage (fetching
    numentries/uuid to build chunks, before any chunk is ever created).
    Coffea's own _preprocess_fileset feeds automatic_retries a bare
    metadata_fetcher, whose success result (a set_accumulator of FileMeta)
    isn't dict-shaped, so a failure there can't ride the same "extra dict
    key" trick used for chunk processing without breaking the accumulator
    merge. Previously this meant metadata-fetch failures were dropped with
    no record at all: _skip_result returned None for them, so they never
    reached self.failed_files, and _filter_badfiles then silently excluded
    the file from the fileset with nothing further logged. Now
    _preprocess_fileset is overridden below to fold results into a plain
    dict with "populated"/"skipped_files" keys instead, so a metadata-fetch
    failure is recorded in self.failed_files exactly like a chunk-processing
    failure.

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

    @property
    def retries(self):
        # DaskExecutor retries at the task level via client.map(retries=...),
        # so automatic_retries must not also retry internally, or a chunk
        # that raises can be retried up to (retries+1)**2 times.
        if isinstance(self.executor, DaskExecutor):
            return 0
        return getattr(self.executor, "retries", 0)

    def run(self, fileset, processor_instance, treename=None):
        # _preprocess_fileset (called inside super().run(), via preprocess())
        # already appended any preprocessing-stage failures to
        # self.failed_files -- extend rather than overwrite so those survive.
        result = super().run(fileset, processor_instance, treename)
        self.failed_files.extend(sorted(result.pop("skipped_files", set_accumulator())))
        self.failed_files.sort()
        return result

    def _preprocess_fileset(self, fileset: Dict) -> None:
        """Same as coffea's Runner._preprocess_fileset, except a file that
        fails to yield metadata (retries exhausted, skipbadfiles=True) is
        recorded into self.failed_files instead of silently contributing
        nothing to the fileset."""
        to_get = set(
            filemeta
            for filemeta in fileset
            if not filemeta.populated(clusters=self.align_clusters)
        )
        if len(to_get) > 0:
            out = {"populated": set_accumulator(), "skipped_files": set_accumulator()}
            pre_arg_override = {
                "function_name": "get_metadata",
                "desc": "Preprocessing",
                "unit": "file",
                "compression": None,
            }
            if isinstance(self.pre_executor, (FuturesExecutor, ParslExecutor)):
                pre_arg_override.update({"tailtimeout": None})
            if isinstance(self.pre_executor, (DaskExecutor)):
                self.pre_executor.heavy_input = None
                pre_arg_override.update({"worker_affinity": False})
            pre_executor = self.pre_executor.copy(**pre_arg_override)
            closure = partial(
                self.automatic_retries,
                self.retries,
                self.skipbadfiles,
                partial(_fetch_populated_metadata, self.xrootdtimeout, self.align_clusters),
            )
            out, _ = pre_executor(to_get, closure, out)
            self.failed_files.extend(sorted(out.get("skipped_files", set_accumulator())))
            populated = out.get("populated", set_accumulator())
            while populated:
                item = populated.pop()
                self.metadata_cache[item] = item.metadata
            for filemeta in fileset:
                filemeta.maybe_populate(self.metadata_cache)

    automatic_retries = staticmethod(_build_automatic_retries())
