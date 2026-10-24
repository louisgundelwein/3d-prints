"""Writes an OrcaSlicer system profile with its `inherits` chain resolved, as the CLI loads it.

Usage: python -I flatten_profile.py KIND NAME OUT.json   (KIND: filament | process | machine)
"""
import json
import os
import sys

kind, name, out = sys.argv[1:4]
base = os.path.expanduser(f"~/.config/OrcaSlicer/system/BBL/{kind}")


def load(n):
    d = json.load(open(os.path.join(base, f"{n}.json")))
    parent = d.pop("inherits", None)
    merged = load(parent) if parent else {}
    merged.update(d)
    return merged


p = load(name)
p.update({"name": name, "from": "system", "instantiation": "true"})
json.dump(p, open(out, "w"), indent=1)
print(out, len(p), "keys")
