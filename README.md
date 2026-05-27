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

# Setting up on the LPC

These instructions are taken from the [`executor_lpc`](https://github.com/PocketCoffea/PocketCoffea/compare/executor_lpc) branch in PocketCoffea.

In order to run jobs on the LPC cluster it is necessary to include the [lpcjobqueue](https://github.com/CoffeaTeam/lpcjobqueue) package in the PocketCoffea singularity environment.
Custom scripts to initialize a shell in an apptainer container with `pocket_coffea` and `lpcjobqueue` are implemented in [PocketCoffea/lpcjobqueue](https://github.com/PocketCoffea/lpcjobqueue).
The apptainer environment is activated on **cmslpc** with the following commands.
From the working directory of your project, download and run the bootstrap script:
```bash
curl -OL https://raw.githubusercontent.com/PocketCoffea/lpcjobqueue/main/bootstrap.sh
bash bootstrap.sh
```
This creates two new files in this directory: `shell` and `.bashrc`. The `./shell`
executable can then be used to start an apptainer shell with a coffea environment.

The default command opens a shell based on the `latest` PocketCoffea image:
```bash
./shell
```

The `pocket-coffea` command inside this image points to a version of python that does not have `lpcjobqueue` installed. To get around this, you need to invoke the runner as a module directly with python. Additionally, you must provide a scaleout parameter or else you will get a single condor worker.
```bash
python -m pocket_coffea.scripts.runner run --cfg config.py --executor dask@lpc --executor-custom-setup executors_lpc.py --outputdir output/ --scaleout 30
```
