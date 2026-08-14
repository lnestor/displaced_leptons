# Displaced Leptons Analysis

CMS Run 3 analysis searching for displaced leptons using the [PocketCoffea](https://pocketcoffea.readthedocs.io) framework. Signal model: stop quarks decaying to a lepton and a displaced vertex (`stopToLD`), producing dilepton final states (ee, μμ, eμ) with large impact parameters.

Jobs run on the Fermilab LPC via Condor.

---

## Project Structure

This analysis uses a customized version of PocketCoffea.


### Supplement Files

Normal NanoAOD files do not have all information we need. We use "supplement" files that are produced via CMSSW. At runtime, we join the supplement files with the central files based on a (run, lumi, event) key. Supplement files are skimmed by trigger, so the join happens after triggers have been processed. We have found that (run, lumi, event) is not necessarily unique in MC, and are searching for a way to solve this problem.


### Object Selection

Normal PocketCoffea recommendations define a set of "good physics objects" and then makes cut on those. This analysis has customized this to track events that fail object selections for cutflow plotting. Object selections can optionally be set as event selections using the `min` keyword in the configuration.


### Custom Processor/Configurator

The PocketCoffea processor and configuration classes have been heavily customized to allow defining everything in the configuration rather than code changes in the processor. The custom processor also adds supplement file joining and individual cut cutflow tracking.

The new keys to the configuration are:

 - `datasets["priority"]`: allows specifying an order to process datasets in
 - `supplements`: points to the supplement definition JSON files, akin to `datasets`
 - `custom_fields`: a list of functions that will define custom fields on the objects passing the skim
 - `object_selections`: a dict whose keys are the name of a collection and values specify which cuts to use. For example, `object_selections["Electron"]: {"min": 1, "cuts": my_cuts}` specifys all electrons must pass `my_cuts`, and at each step 1 electron must pass. Any events who don't have a single electron passing will be dropped. This is where object selections can act as event selections
 - `event_preselections`: renamed from `preselections` for clarity


### File Structure

Below are some notable directories and files.

| File/Dir | Purpose |
|---|---|
| `configs` | Top-level configurations for different channels |
| `workflow.py` | `DisplacedLeptonProcessor` — applies object and event selection |
| `lib/` | Contains non-script related code that is meant to be shared in analysis code |
| `scripts/` | Contains scripts and shared code that is to be run after analysis jobs finish |
| `object_selection.py` | Cut definitions for specific physics objects |
| `event_selection.py` | Cut definitions for entire events |
| `params/` | YAML parameter files (object selection, triggers, regions) |
| `datasets/` | Dataset and supplement JSON files for PocketCoffea input |
| `datasets/sources/datasets.yaml` | Single source of truth for all dataset information |
