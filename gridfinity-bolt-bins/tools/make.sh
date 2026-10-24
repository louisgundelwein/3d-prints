#!/bin/bash
# Rebuilds cad/, stl/, orca/bins/, orca/Gridfinity_Bolt_Bins.3mf and images/ from tools/build.py;
# fails on a kernel defect, text too near the lip or an OrcaSlicer error.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I tools/make.py
