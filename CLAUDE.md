# Displaced Leptons Analysis

CMS Run 3 analysis searching for displaced leptons using the [PocketCoffea](https://pocketcoffea.readthedocs.io) framework. Signal model: stop quarks decaying to a lepton and a displaced vertex (`stopToLD`), producing dilepton final states (ee, μμ, eμ) with large impact parameters.

Jobs run on the Fermilab LPC via Condor.

---

## Project Structure

This analysis uses a customized version of PocketCoffea.


### Supplement Files

Normal NanoAOD files do not have all information we need. We use "supplement" files that are produced via CMSSW. At runtime, we join the supplement files with the central files based on a (run, lumi, event) key. Supplement files are skimmed by trigger, so the join happens after triggers have been processed. We have found that (run, lumi, event) is not necessarily unique in MC, and are searching for a way to solve this problem.


### Object Selection

Object cuts are defined in the configuration (`object_selections`) rather than hardcoded in the processor, and build the `{coll}Good` collections. Object selections never drop events; require a number of good objects with an event preselection instead (e.g. `get_nObj_min(2, coll="ElectronGood")`).


### Custom Processor/Configurator

The PocketCoffea processor and configuration classes have been heavily customized to allow defining everything in the configuration rather than code changes in the processor. The custom processor also adds supplement file joining (see `lib/workflow/supplement.py`).

The new keys to the configuration are:

 - `datasets["priority"]`: allows specifying an order to process datasets in
 - `supplements`: points to the supplement definition JSON files, akin to `datasets`
 - `custom_fields`: a list of functions that will define custom fields on the objects passing the skim
 - `object_selections`: a dict mapping a collection name to its list of object cuts. For example, `object_selections["Electron"] = my_cuts` builds `ElectronGood` from electrons passing all of `my_cuts`
 - `event_preselections`: renamed from `preselections` for clarity


### File Structure

Below are some notable directories and files.

| File/Dir | Purpose |
|---|---|
| `configs` | Top-level configurations for different channels |
| `lib/workflow/analysis_processor.py` | `AnalysisProcessor` - builds good objects from the config, runs custom fields, joins supplement files |
| `lib/` | Contains non-script related code that is meant to be shared in analysis code |
| `scripts/` | Contains scripts and shared code that is to be run after analysis jobs finish |
| `object_selection.py` | Cut definitions for specific physics objects |
| `event_selection.py` | Cut definitions for entire events |
| `params/` | YAML parameter files (object selection, triggers, regions) |
| `datasets/` | Dataset and supplement JSON files for PocketCoffea input |
| `datasets/sources/datasets.yaml` | Single source of truth for all dataset information |
