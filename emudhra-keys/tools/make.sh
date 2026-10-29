#!/bin/bash
# Rebuilds cad/, stl/, orca/eMudhra_Keys.3mf and images/ from tools/build.py; fails on a kernel
# defect, overlapping parts, digits too near the edge or an OrcaSlicer error.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I tools/make.py
