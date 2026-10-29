"""Rebuilds every print file from build.py: per key the parametric design cad/<key>.solidcraft and
the STLs of its plaque and digits in stl/, the mount's STL once (it is the same for every key),
orca/eMudhra_Keys.3mf with one plate per key (plaque, digits, mount) and the picture in images/.
In the 3MF each plaque is one object of two parts: the plaque on filament 1, the digits on filament 2.

Stops with an error when a design has a kernel defect (build.defects), when the mount and the
plaque overlap, when the digits come nearer than MARGIN to the plaque's edge, or when OrcaSlicer fails.

Usage: python -I make.py   (from anywhere; needs solidcraft-cli, orca-slicer and magick on the PATH)
"""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORK = os.path.join(ROOT, "work")
MARGIN = 15.0   # mm the digits keep from the plaque's edge at least
BED = 256.0
GAP = 10.0      # mm between plaque and mount on the plate


def bbox(path):
    """(min, max) corners of a binary STL."""
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for i in range(n):
        v = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
        for k in range(9):
            lo[k % 3] = min(lo[k % 3], v[k])
            hi[k % 3] = max(hi[k % 3], v[k])
    return lo, hi


def run(script, save=None):
    """Runs a script; returns the per-command results."""
    path = os.path.join(WORK, "script.json")
    out = os.path.join(WORK, "results.json")
    json.dump(script, open(path, "w"))
    cmd = ["solidcraft-cli", "run", path, "--quiet", "--results", "--json-out", out] + (["--save", save] if save else [])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return json.load(open(out))


def evaluate(path):
    """`solidcraft-cli eval` of a script or design file."""
    out = os.path.join(WORK, "eval.json")
    subprocess.run(["solidcraft-cli", "eval", path, "--json-out", out], check=True, stdout=subprocess.DEVNULL)
    return json.load(open(out))


def number_box(key, text=None):
    """Outline (min, max) of the key's digits."""
    path = os.path.join(WORK, "text.json")
    json.dump(build.text_script(key, text), open(path, "w"))
    b = next(b for b in evaluate(path)["bodies"] if b["name"] == "Number")["bbox"]
    return b["min"], b["max"]


def fit_text(key):
    """Text overrides that centre the digits on the plaque by their measured outline."""
    lo, hi = number_box(key)
    return {"text_dx": f"{-(lo[0] + hi[0]) / 2:.4f} mm", "text_dy": f"{-(lo[1] + hi[1]) / 2:.4f} mm"}


def interference(results):
    """The result of the script's inspect.interference command."""
    found = [r for r in walk(results) if "interferences" in r]
    if len(found) != 1:
        raise SystemExit(f"expected one interference result, found {len(found)}")
    return found[0]


def walk(node):
    """Every dict in a nested result."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def export_key(key):
    """The key's design, checked, and its STLs (and the mount's)."""
    text = fit_text(key)
    d = build.script(key, text)
    d["commands"].append({"command": "inspect.interference", "params": {}})
    for body in ("Plaque", "Number"):
        d["commands"].append({"command": "file.export", "params": {"path": os.path.join(ROOT, "stl", f"{key}_{body.lower()}.stl"), "bodies": [body]}})
    d["commands"].append({"command": "file.export", "params": {"path": os.path.join(ROOT, "stl", "mount.stl"), "bodies": ["Mount"]}})
    design = os.path.join(ROOT, "cad", f"{key}.solidcraft")
    hits = interference(run(d, save=design))
    problems = build.defects(evaluate(design))
    if hits["count"] or hits["truncated"] or hits["pairs_not_checked"] or hits["unchecked"]:
        problems.append(f"bodies overlap or were not checked: {hits['interferences']} {hits['unchecked']}")
    V = build.values(key, text)
    lo, hi = bbox(os.path.join(ROOT, "stl", f"{key}_number.stl"))
    margins = [V["plaque_w"] / 2 + lo[0], V["plaque_w"] / 2 - hi[0], V["plaque_h"] / 2 + lo[1], V["plaque_h"] / 2 - hi[1]]
    if min(margins) < MARGIN or max(abs(lo[0] + hi[0]), abs(lo[1] + hi[1])) / 2 > 0.01:
        problems.append(f"digits not centred with {MARGIN} mm margin: {[round(m, 2) for m in margins]}")
    if problems:
        raise SystemExit(f"{key}: " + "; ".join(problems))
    print(f"{key}: plaque {V['plaque_w']:g} x {V['plaque_h']:g} mm, margins {min(margins):.1f} mm, eval clean, no overlap", flush=True)


def plate(key):
    """One plate: the plaque (two parts) centred at the front, the mount behind it."""
    objects = []
    plaque = [os.path.join(ROOT, "stl", f"{key}_{p}.stl") for p in ("plaque", "number")]
    mount = os.path.join(ROOT, "stl", "mount.stl")
    (plo, phi), (mlo, mhi) = bbox(plaque[0]), bbox(mount)
    pw, ph, mw, mh = phi[0] - plo[0], phi[1] - plo[1], mhi[0] - mlo[0], mhi[1] - mlo[1]
    y0 = (BED - ph - GAP - mh) / 2
    if y0 < 28:   # P1S excluded corner, 18 x 28 mm at the front left
        raise SystemExit(f"{key}: plate too full")
    # pos moves the STL's own coordinates; plaque and digits share the plaque's frame, so the same move
    for path, fil in zip(plaque, (1, 2)):
        objects.append({"path": path, "count": 1, "filaments": [fil], "assemble_index": [1],
                        "pos_x": [(BED - pw) / 2 - plo[0]], "pos_y": [y0 - plo[1]], "pos_z": [-plo[2]]})
    objects.append({"path": mount, "count": 1, "filaments": [1], "assemble_index": [2],
                    "pos_x": [(BED - mw) / 2 - mlo[0]], "pos_y": [y0 + ph + GAP - mlo[1]], "pos_z": [-mlo[2]]})
    return {"plate_name": f"Key {key}", "need_arrange": False, "objects": objects}


def orca(out_path):
    settings = os.path.join(ROOT, "orca", "settings")
    json.dump({"plates": [plate(k) for k in build.KEYS]}, open(os.path.join(settings, "assemble.json"), "w"), indent=1)
    with tempfile.TemporaryDirectory() as out:
        r = subprocess.run(["orca-slicer", "--load-settings", "machine.json;process.json", "--load-filaments", "petg_hf_black.json;petg_hf_white.json",
                            "--load-assemble-list", "assemble.json", "--outputdir", out, "--export-3mf", "out.3mf"],
                           cwd=settings, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(os.path.join(out, "out.3mf")):
            raise SystemExit(f"orca-slicer failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
        shutil.move(os.path.join(out, "out.3mf"), out_path)
    os.remove(os.path.join(settings, "assemble.json"))
    for f in os.listdir(settings):
        if f.endswith(".log"):
            os.remove(os.path.join(settings, f))


def picture(key, name, view, script=None):
    """A trimmed snapshot of the key's design into images/; script runs on top of the design first."""
    shot = os.path.join(WORK, f"{name}.png")
    cmd = ["solidcraft-cli", "snapshot"]
    if script:
        path = os.path.join(WORK, "picture.json")
        json.dump({"commands": script}, open(path, "w"))
        cmd += [path, "--in"]
    cmd += [os.path.join(ROOT, "cad", f"{key}.solidcraft"), "--out", shot, "--width", "1200", "--height", "900", "--no-grid", "--no-axes"] + view
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["magick", shot, "-trim", "-resize", "700x", os.path.join(ROOT, "images", f"{name}.png")], check=True)


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    for key in build.KEYS:
        export_key(key)
    orca(os.path.join(ROOT, "orca", "eMudhra_Keys.3mf"))
    picture(237, "front", ["--view", "top"])
    # the back, the mount slid down off the rail and lighter
    picture(237, "back", ["--camera", json.dumps({"target": [0, -50, 0], "yaw": 0.5, "pitch": -0.9, "distance": 300})], [
        {"command": "solid.move", "params": {"bodies": ["Mount"], "translate": [0, -100, 0]}},
        {"command": "appearance.assign", "params": {"bodies": ["Mount"], "color": "#8c8f94"}},
        {"command": "appearance.assign", "params": {"bodies": ["Plaque"], "color": "#45484d"}}])
