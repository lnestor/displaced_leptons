# Displaced Leptons Analysis — lxplus Project

This directory (`~/leptons` on lxplus) contains a CMS analysis searching for displaced leptons, using the [PocketCoffea](https://pocketcoffea.readthedocs.io) framework. The signal model is DisplacedSUSY: stop quarks decaying to a lepton and a displaced vertex (`stopToLD`), producing dilepton final states (ee, μμ, eμ) with large impact parameters.

---

## Environment

All analysis code runs inside an Apptainer container. Launch it with:

```bash
apptainer shell \
  -B /afs -B /cvmfs/cms-griddata.cern.ch/ -B /cvmfs/cms.cern.ch \
  -B /tmp -B /eos/cms -B /etc/sysconfig/ngbauth-submit \
  -B ${XDG_RUNTIME_DIR} \
  --env KRB5CCNAME="FILE:${XDG_RUNTIME_DIR}/krb5cc" \
  /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/pocketcoffea:lxplus-el9-latest/
```

`pocket_coffea` is provided by the container — do not try to install it locally.

---

## File Structure

| File/Dir | Purpose |
|---|---|
| `config.py` | Top-level PocketCoffea `Configurator` — datasets, skim, categories, histograms |
| `workflow.py` | `DisplacedLeptonProcessor` — applies object and event selection |
| `object_selection.py` | `displaced_lepton_selection()` — pt, eta, ID, isolation, SC gap cuts for e/μ |
| `event_selection.py` | Cut definitions: `dilepton_presel`, `no_b2b_muons`, `dilepton_pair`, `get_nElectrons/Muons` |
| `custom_cuts.py` | Additional custom cut functions |
| `params/` | YAML parameter files (object preselection, triggers, categories, plotting) |
| `datasets/` | Dataset JSON files for PocketCoffea input |
| `output_test/` | Output from test runs |
| `plots/` | Output plots, organized by category |

---

## Analysis Overview

**Signal**: `DisplacedSUSY_stopToLD_M_200_1mm` — stop mass 200 GeV, cτ = 1 mm, 13 TeV, 2017

**Selection flow**:
1. **Skim**: event flags, golden JSON, ≥1 good PV, HLT (EMu primary dataset)
2. **Preselection**: ≥2 good leptons total (`dilepton_presel`)
3. **Categories** (currently only `baseline` active; ee/eμ/μμ splits commented out):
   - `emu`: no back-to-back muons, ΔR > 0.2, ≥1 e + ≥1 μ passing category-specific pt thresholds
   - `mumu`: no back-to-back muons, ΔR > 0.2, ≥2 μ
   - `ee`: ΔR > 0.2, ≥2 e

**Object selection** (`object_selection.py`): pt, |η|, optional η-φ veto, lepton ID, supercluster gap veto (electrons), isolation (pt-dependent for electrons in Run 2 except 2016)

---

## Running

Inside the Apptainer container, from `~/leptons`:

```bash
# Test run
pocket-coffea run --cfg config.py -o output_test/

# Check output
pocket-coffea plot --cfg config.py -i output_test/ -o plots/
```
