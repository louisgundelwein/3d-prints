#!/bin/bash
# Rebuilds everything from tools/build.py: cad/rack.solidcraft, the STLs in print orientation and
# orca/MacMini_Rack.3mf. With --macs MAC.step it also writes work/rack_with_macs.solidcraft to check the fit.
set -euo pipefail
macs=""
if [ $# -eq 2 ] && [ "$1" = "--macs" ]; then
  macs=$(realpath -e "$2")
elif [ $# -ne 0 ]; then
  echo "usage: $0 [--macs MAC.step]" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
mkdir -p work
python3 -I tools/build.py work/rack.json
python3 -I - "$PWD/work" <<'PY'
import json, sys
work = sys.argv[1]
d = json.load(open(f"{work}/rack.json"))
for body in ("Rack_links", "Rack_rechts", "Riegel_1"):
    d["commands"].append({"command": "file.export", "params": {"path": f"{work}/{body}.stl", "bodies": [body]}})
json.dump(d, open(f"{work}/export.json", "w"))
PY
solidcraft-cli run work/export.json --save cad/rack.solidcraft --quiet
# halves: front face on the bed (model Y up); latch: the face against the faceplate on the bed
python3 -I tools/orient_stl.py work/Rack_links.stl stl/Rack_links.stl 1,0,0,0,0,-1,0,1,0
python3 -I tools/orient_stl.py work/Rack_rechts.stl stl/Rack_rechts.stl 1,0,0,0,0,-1,0,1,0
python3 -I tools/orient_stl.py work/Riegel_1.stl stl/Riegel.stl 1,0,0,0,0,1,0,-1,0
tools/orca_project.sh
rm -f orca/settings/*.log
if [ -n "$macs" ]; then
  python3 -I tools/build.py work/rack_with_macs.json --macs "$macs"
  solidcraft-cli run work/rack_with_macs.json --save work/rack_with_macs.solidcraft --quiet
fi
