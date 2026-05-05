# Setting up on the old tier 3

Initial setup

```
micromamba create -n pocket-coffea python=3.9 -c conda-forge
micromamba activate pocket-coffea

micromamba install -c conda-forge coffea awkward uproot fsspec-xrootd xrootd numpy scipy matplotlib "pyarrow<8" -y

pip install pocket-coffea

```

Normal running

```
micromamba activate pocket-coffea
pocket-coffea run --cfg config.py --test --outputdir output_test
```

Need to use the `_global` database files. Still working on why. At lxplus can use the normal ones.
