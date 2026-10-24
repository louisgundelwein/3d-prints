"""Builds a bin in the running SolidCraft GUI, one named step of build.py at a time, so the
window shows it grow. Saves a screenshot per step into SHOTS; stops on any warning or nudged boolean.

Usage: python -I live.py SHOTS [--label TEXT] [--cells X Y] [--no-magnets] [--from N] [--new]
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build import cells_for, steps  # noqa: E402
from make import WORK, fit_text  # noqa: E402
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


def walk(node, found):
    """Collects warnings and nudged booleans (build.defects' rules) from a batch result."""
    if isinstance(node, dict):
        if node.get("warning"):
            found.append(node["warning"])
        if node.get("strategy") and node["strategy"] not in ("refined_tolerance", "planar_fallback"):
            found.append(node["strategy"])
        for v in node.values():
            walk(v, found)
    elif isinstance(node, list):
        for v in node:
            walk(v, found)


g = Gui()
if new:
    g.call("new_design", {"name": f"Gridfinity {label}"})
cx = cx or cells_for(label)
os.makedirs(WORK, exist_ok=True)
text = fit_text(label, cx)[0] if cy == 1 else None   # centred and fitted as make.py does
for n, (name, cmds) in enumerate(steps(label, cx, cy, magnets, text)):
    if n < start:
        continue
    out = g.call("batch", {"commands": cmds})
    found = []
    for c in out:
        if c.get("type") == "text":
            walk(json.loads(c["text"]), found)
    if found:
        raise SystemExit(f"step {n} {name}: kernel defects: {found}")
    print(f"step {n} {name}: {len(cmds)} commands, no warnings")
    for c in g.call("screenshot", {"grid": False, "axes": False}):
        if c.get("type") == "image":
            open(f"{shots}/{n:02d}_{name}.png", "wb").write(base64.b64decode(c["data"]))
