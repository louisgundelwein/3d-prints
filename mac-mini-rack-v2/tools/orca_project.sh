#!/bin/bash
# Rebuilds orca/MacMini_Rack.3mf from the STLs (plate 1: left half, plate 2: right half and the latches).
set -e
cd "$(dirname "$0")/../orca/settings"
out=$(mktemp -d)
orca-slicer --load-settings "machine.json;process.json" --load-filaments "petg.json" \
  --load-assemble-list assemble.json --outputdir "$out" --export-3mf MacMini_Rack.3mf
mv "$out/MacMini_Rack.3mf" ../MacMini_Rack.3mf
