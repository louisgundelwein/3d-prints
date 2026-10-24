#!/bin/bash
# Rebuilds stl/, cad/ and orca/Gridfinity_Bolt_Bins.3mf from tools/build.py.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I tools/make.py
