#!/bin/bash
# Rebuild supplements/EGamma.json from scratch.
# Run from the displaced_leptons repo root on the LPC.
set -e

OUT=supplements/EGamma.json

if [ -f "$OUT" ]; then
    mv "$OUT" "$OUT.bak"
    echo "Backed up existing $OUT to $OUT.bak"
fi

run() {
    echo "=== $* ==="
    python3 scripts/datasets/create_supplement_definition.py "$@"
}

# Era C
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024C --dataset /EGamma0/Run2024C-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraC --year 2024 --era C --sample EGamma --overwrite
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024C --dataset /EGamma1/Run2024C-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraC --year 2024 --era C --sample EGamma --append

# Era D
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024D --dataset /EGamma0/Run2024D-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraD --year 2024 --era D --sample EGamma --overwrite
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024D --dataset /EGamma1/Run2024D-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraD --year 2024 --era D --sample EGamma --append

# Era E (EGamma1 only -- no EGamma0_Run2024E on EOS)
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024E --dataset /EGamma1/Run2024E-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraE --year 2024 --era E --sample EGamma --overwrite

# Era G (EGamma0 only -- no EGamma1_Run2024G on EOS)
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024G --dataset /EGamma0/Run2024G-MINIv6NANOv15-v2/NANOAOD --output "$OUT" --key EGamma_Run2024_EraG --year 2024 --era G --sample EGamma --overwrite

# Era H
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024H --dataset /EGamma0/Run2024H-MINIv6NANOv15-v2/NANOAOD --output "$OUT" --key EGamma_Run2024_EraH --year 2024 --era H --sample EGamma --overwrite
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024H --dataset /EGamma1/Run2024H-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraH --year 2024 --era H --sample EGamma --append

# Era I (v1 and v2 for both PDs, all merged into one era per datasets_data_run3.json)
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024I --dataset /EGamma0/Run2024I-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraI --year 2024 --era I --sample EGamma --overwrite
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024I --dataset /EGamma1/Run2024I-MINIv6NANOv15-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraI --year 2024 --era I --sample EGamma --append
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma0_Run2024I_v2 --dataset /EGamma0/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraI --year 2024 --era I --sample EGamma --append
run --eos-dir root://cmseos.fnal.gov//store/user/lnestor/supplements/EGamma1_Run2024I_v2 --dataset /EGamma1/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD --output "$OUT" --key EGamma_Run2024_EraI --year 2024 --era I --sample EGamma --append

echo "Done. Wrote keys for eras: C D E G H I"
