"""Builds a key's number and mount in the running SolidCraft GUI, one named step of build.py at a time, so the
window shows it grow. Saves a screenshot per step into SHOTS; stops on any warning or nudged boolean.

Usage: python -I live.py SHOTS [KEY] [--new]
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build import steps  # noqa: E402
from make import WORK, place, walk  # noqa: E402
from gui import Gui  # noqa: E402

args = sys.argv[1:]
new = "--new" in args
args = [a for a in args if a != "--new"]
shots, key = args[0], int(args[1]) if len(args) > 1 else 237
os.makedirs(shots, exist_ok=True)
os.makedirs(WORK, exist_ok=True)

g = Gui()
if new:
    g.call("new_design", {"name": f"eMudhra key {key}"})
mx, my0, _ = place(key, {})
for n, (name, cmds) in enumerate(steps(key, {"mx": f"{mx} mm", "my0": f"{my0} mm"})):
    out = g.call("batch", {"commands": cmds})
    found = []
    for c in out:
        if c.get("type") == "text":
            for d in walk(json.loads(c["text"])):
                if d.get("warning"):
                    found.append(d["warning"])
                if d.get("strategy") and d["strategy"] not in ("refined_tolerance", "planar_fallback"):
                    found.append(d["strategy"])
    if found:
        raise SystemExit(f"step {n} {name}: kernel defects: {found}")
    print(f"step {n} {name}: {len(cmds)} commands, no warnings", flush=True)
    for c in g.call("screenshot", {"grid": False, "axes": False}):
        if c.get("type") == "image":
            open(f"{shots}/{n:02d}_{name.replace(' ', '_')}.png", "wb").write(base64.b64decode(c["data"]))
