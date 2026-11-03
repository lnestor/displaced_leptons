import json

import awkward as ak
import numpy as np
import uproot

from lib.workflow.supplement import SupplementPlugin

CENTRAL_LFN = "/store/f1.root"
CENTRAL_FILENAME = "root://host/" + CENTRAL_LFN


def make_events(keys):
    run, lumi, event = (np.array(col, dtype=np.uint32) for col in zip(*keys))
    return ak.Array({"run": run, "luminosityBlock": lumi, "event": event.astype(np.uint64)})


def write_supplement(path, keys):
    run, lumi, event = (np.array(col) for col in zip(*keys))
    with uproot.recreate(path) as f:
        f["supplementTree/Events"] = {
            "run": run.astype(np.uint32),
            "luminosityBlock": lumi.astype(np.uint32),
            "event": event.astype(np.uint64),
            "Coll_field1": np.arange(len(keys), dtype=np.float32),
        }
    return str(path)


def make_plugin(tmp_path, files=None, version=1, rejected_lumis=None, diagnostics=None):
    definition = {"metadata": {"dataset": "ds1", "version": version}, "files": files or {}}
    if rejected_lumis is not None:
        definition["rejected_lumis"] = rejected_lumis

    json_path = tmp_path / "supplements.json"
    json_path.write_text(json.dumps({"key1": definition}))

    diagnostics = {} if diagnostics is None else diagnostics
    return SupplementPlugin([str(json_path)], ["ds1"], diagnostics, "ds1")


def test_drop_rejected_lumis_removes_only_events_in_rejected_lumis(tmp_path):
    plugin = make_plugin(tmp_path, rejected_lumis=[[1, 2]])
    events = make_events([(1, 1, 10), (1, 2, 20), (1, 3, 30), (2, 2, 40)])

    kept = plugin.drop_rejected_lumis(events)

    assert ak.to_list(kept.event) == [10, 30, 40]


def test_drop_rejected_lumis_keeps_all_events_without_rejected_lumis(tmp_path):
    plugin = make_plugin(tmp_path)
    events = make_events([(1, 1, 10), (1, 2, 20)])

    kept = plugin.drop_rejected_lumis(events)

    assert ak.to_list(kept.event) == [10, 20]


def test_drop_rejected_lumis_counts_removed_events_in_diagnostics(tmp_path):
    diagnostics = {}
    plugin = make_plugin(tmp_path, rejected_lumis=[[1, 2]], diagnostics=diagnostics)

    plugin.drop_rejected_lumis(make_events([(1, 1, 10), (1, 2, 20), (1, 2, 21)]))

    assert diagnostics["ds1"]["events_in_rejected_lumis"] == 2


def test_join_returns_no_unmatched_events_without_supplement_definition(tmp_path):
    plugin = SupplementPlugin([], ["ds1"], {}, "ds1")
    events = make_events([(1, 1, 10), (1, 2, 20)])

    joined, unmatched = plugin.join(events, CENTRAL_FILENAME)

    assert ak.to_list(joined.event) == [10, 20]
    assert len(unmatched) == 0
    assert "event" in unmatched.fields


def test_join_returns_all_events_as_unmatched_when_chunk_has_no_supplement_file(tmp_path):
    plugin = make_plugin(tmp_path)
    events = make_events([(1, 1, 10), (1, 2, 20)])

    joined, unmatched = plugin.join(events, CENTRAL_FILENAME)

    assert len(joined) == 0
    assert ak.to_list(unmatched.event) == [10, 20]


def test_join_returns_events_without_supplement_row_as_unmatched(tmp_path):
    supp_path = write_supplement(tmp_path / "supp.root", [(1, 1, 10), (1, 1, 30)])
    plugin = make_plugin(tmp_path, files={CENTRAL_LFN: [supp_path]})
    events = make_events([(1, 1, 10), (1, 1, 20), (1, 1, 30)])

    joined, unmatched = plugin.join(events, CENTRAL_FILENAME)

    assert ak.to_list(joined.event) == [10, 30]
    assert ak.to_list(unmatched.event) == [20]
