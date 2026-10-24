"""Builds a bin in the running SolidCraft GUI, one named step of build.py at a time, so the
window shows it grow. Saves a screenshot per step into SHOTS.

Usage: python -I live.py SHOTS [--label TEXT] [--cells X Y] [--no-magnets] [--from N] [--new]
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build import cells_for, steps  # noqa: E402
from gui import Gui  # noqa: E402

args = sys.argv[1:]
shots = args.pop(0)
label, cx, cy, magnets, start, new = "M5x10", None, 1, True, 0, False
if "--label" in args:
    i = args.index("--label"); label = args[i + 1]; del args[i:i + 2]
if "--cells" in args:
    i = args.index("--cells"); cx, cy = int(args[i + 1]), int(args[i + 2]); del args[i:i + 3]
if "--no-magnets" in args:
    args.remove("--no-magnets"); magnets = False
if "--from" in args:
    i = args.index("--from"); start = int(args[i + 1]); del args[i:i + 2]
if "--new" in args:
    args.remove("--new"); new = True
os.makedirs(shots, exist_ok=True)
g = Gui()
if new:
    g.call("new_design", {"name": f"Gridfinity {label}"})
for n, (name, cmds) in enumerate(steps(label, cx or cells_for(label), cy, magnets)):
    if n < start:
        continue
    out = g.call("batch", {"commands": cmds})
    text = " ".join(c.get("text", "") for c in out)
    import re
    warn = [w for w in ("tool_nudge", "coplanar_separation") if w in text] + re.findall(r'"warning": "([^"]*)"', text)
    print(f"step {n} {name}: {len(cmds)} commands ok", warn or "")
    for c in g.call("screenshot", {"grid": False, "axes": False}):
        if c.get("type") == "image":
            open(f"{shots}/{n:02d}_{name}.png", "wb").write(base64.b64decode(c["data"]))
