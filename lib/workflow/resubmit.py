from coffea.processor import accumulate


def _undo_sumgenweights_scaling(processor, output):
    inverted = dict(output)
    for key in ("sum_genweights", "sum_signOf_genweights"):
        inverted[key] = {ds: 1 / v for ds, v in output.get(key, {}).items() if v}
    processor.rescale_sumgenweights(inverted)


def merge_partial_output(processor, existing, partial):
    """Merge a postprocessed output from a files-only resubmission onto the
    postprocessed output of the same dataset. Each was normalized by its own
    sum_genweights, so both are unscaled, summed, and postprocessed again to
    normalize by the combined sum_genweights. datasets_metadata is dropped
    before summing since accumulate() would concatenate its strings;
    postprocess rebuilds it."""
    for output in (existing, partial):
        output.pop("datasets_metadata", None)
        _undo_sumgenweights_scaling(processor, output)
    return processor.postprocess(accumulate([existing, partial]))
