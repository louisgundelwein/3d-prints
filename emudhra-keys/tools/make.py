"""Rebuilds every print file from build.py: per key the parametric design cad/<key>.solidcraft and
the number's STL in stl/, a 1:1 drilling template templates/<key>.pdf, the mount's STL once (it is the same for every key, checked),
orca/eMudhra_Keys.3mf with one plate per key (number and mount) and the pictures in images/.

Per key it measures the digits, checks they are one connected piece, and places
the slot where its footprint (build.footprint) lies inside the digits, as near the centre of mass
as it can along X. Stops with an error when no place fits, when a design has a kernel defect
(build.defects), when the mount and the number overlap, or when OrcaSlicer fails.

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

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORK = os.path.join(ROOT, "work")
BED = 256.0
GAP = 10.0      # mm between number and mount on the plate
RES = 0.2       # mm per pixel of the digits' raster
JOIN_AREA = 150.0   # mm² neighbouring digits share at least (10 mm thick: a joint of 1500 mm³)
JOIN_MAX = 20.0     # mm the outlines may overlap at most before the number gets unreadable


def triangles(path):
    """Triangles of a binary STL as an (n, 3, 3) array."""
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    return np.array([struct.unpack_from("<9f", data, 84 + 50 * i + 12) for i in range(n)]).reshape(-1, 3, 3)


def bbox(path):
    t = triangles(path)
    return t.min((0, 1)), t.max((0, 1))


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


def walk(node):
    """Every dict in a nested result."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def glyph(d):
    """One digit, its outline centred on X = 0 (as build.centres places a lone digit), as a boolean array on a fixed grid (rows along Y,
    X and Y from -GRID to GRID)."""
    stl = os.path.join(WORK, f"glyph_{d}.stl")
    over = {"mx": "0 mm", "my0": "0 mm"}
    cmds = build.text_script(int(d), over)["commands"]
    cmds.append({"command": "file.export", "params": {"path": stl, "bodies": ["Number"]}})
    run({"commands": cmds})
    n = int(2 * GRID / RES)
    img = Image.new("1", (n, n), 0)
    draw = ImageDraw.Draw(img)
    for tri in triangles(stl):
        draw.polygon([((p[0] + GRID) / RES, (p[1] + GRID) / RES) for p in tri], fill=1)
    return np.array(img, dtype=bool)


GRID = 80.0   # mm half size of a glyph's raster


def find_joins(key):
    """Per pair of digits the smallest overlap of their outlines (0.5 mm steps) at which they share
    JOIN_AREA, as parameter overrides."""
    digits = str(key)
    V = build.values()
    out = {}
    for name, a, b in zip(build.joins(key), digits, digits[1:]):
        A, B = glyph(a), glyph(b)
        # distance of the outlines' centres with the outlines just touching
        apart = (build.INK[a][1] - build.INK[a][0] + build.INK[b][1] - build.INK[b][0]) / 2 * V["text_h"]
        for k in range(int(JOIN_MAX / 0.5) + 1):
            o = k * 0.5
            shift = int(round((apart - o) / RES))
            shared = (A[:, shift:] & B[:, :B.shape[1] - shift]).sum() * RES * RES
            if shared >= JOIN_AREA:
                out[name] = f"{o} mm"
                break
        else:
            raise SystemExit(f"{key}: digits {a}{b} share under {JOIN_AREA} mm² even {JOIN_MAX} mm into each other")
    return out


def raster(key, over):
    """The digits seen from the front as a boolean array (rows along Y), and its origin."""
    stl = os.path.join(WORK, "digits.stl")
    d = build.text_script(key, over)
    d["commands"].append({"command": "file.export", "params": {"path": stl, "bodies": ["Number"]}})
    run(d)
    t = triangles(stl)
    lo, hi = t.min((0, 1)), t.max((0, 1))
    img = Image.new("1", (int((hi[0] - lo[0]) / RES) + 3, int((hi[1] - lo[1]) / RES) + 3), 0)
    draw = ImageDraw.Draw(img)
    for tri in t:
        draw.polygon([((p[0] - lo[0]) / RES + 1, (p[1] - lo[1]) / RES + 1) for p in tri], fill=1)
    # one piece: a flood fill from any pixel of the digits reaches all of them
    filled = img.convert("L")
    ys, xs = np.nonzero(np.array(img))
    ImageDraw.floodfill(filled, (int(xs[0]), int(ys[0])), 128)
    if (np.array(filled) == 255).any():
        raise SystemExit(f"{key}: the digits are not one piece; raise overlap")
    return np.array(img, dtype=np.int64), (lo[0] - RES, lo[1] - RES)


def place(key, over):
    """mx, my0: where the slot's footprint lies inside the digits, nearest the centre of mass along X
    (the wedge holds the number level, but the less it has to the better), highest among those."""
    m, (ox, oy) = raster(key, over)
    x0, x1, y0, y1 = build.footprint(build.values(over))
    x0, x1, y0, y1 = x0 - RES, x1 + RES, y0 - RES, y1 + RES   # the raster's edge pixels are partly outside
    a, b = math.ceil((x1 - x0) / RES), math.ceil((y1 - y0) / RES)
    s = np.pad(m.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    inside = (s[b:, a:] - s[:-b, a:] - s[b:, :-a] + s[:-b, :-a]) == a * b
    fits = np.argwhere(inside)
    if not len(fits):
        raise SystemExit(f"{key}: no place for the slot inside the digits")
    ys, xs = np.nonzero(m)
    com_x = xs.mean() * RES + ox
    mx = fits[:, 1] * RES + ox - x0
    my0 = fits[:, 0] * RES + oy - y0
    best = np.lexsort((-my0, np.round(abs(mx - com_x), 1)))[0]
    return round(float(mx[best]), 2), round(float(my0[best]), 2), com_x


def export_key(key):
    """The key's design, checked, and its STLs. Returns the mount STL's hash."""
    over = {"mx": "0 mm", "my0": "0 mm", **find_joins(key)}
    mx, my0, com_x = place(key, over)
    over.update({"mx": f"{mx} mm", "my0": f"{my0} mm"})
    d = build.script(key, over)
    d["commands"].append({"command": "inspect.interference", "params": {}})
    number, mount = os.path.join(ROOT, "stl", f"{key}.stl"), os.path.join(WORK, f"mount_{key}.stl")
    d["commands"].append({"command": "file.export", "params": {"path": number, "bodies": ["Number"]}})
    d["commands"].append({"command": "file.export", "params": {"path": mount, "bodies": ["Mount"]}})
    design = os.path.join(ROOT, "cad", f"{key}.solidcraft")
    hits = [r for r in walk(run(d, save=design)) if "interferences" in r]
    problems = build.defects(evaluate(design))
    if len(hits) != 1 or hits[0]["count"] or hits[0]["truncated"] or hits[0]["pairs_not_checked"] or hits[0]["unchecked"]:
        problems.append(f"number and mount overlap or were not checked: {hits}")
    bodies = {b["name"]: b for b in evaluate(design)["bodies"]}
    shells = bodies["Number"]["kernel"]["shells"]
    if shells != 1:
        problems.append(f"the number is {shells} shells, not one piece")
    if problems:
        raise SystemExit(f"{key}: " + "; ".join(problems))
    lo, hi = bbox(number)
    V = build.values(over)
    joined = ", ".join(over[k] for k in build.joins(key))
    template(key, over)
    print(f"{key}: {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} mm, joins [{joined}], rail {mx - com_x:+.1f} mm from the centre of mass; "
          f"lower screw {mx - lo[0]:.0f} mm from the left edge, {my0 + V['hole_y1'] - lo[1]:.0f} mm above the bottom edge; "
          "eval clean, no overlap", flush=True)
    # the mount must be the same for every key: its shape, wherever it sits
    b = bodies["Mount"]
    shape = (round(b["volume_mm3"], 2), round(b["area_mm2"], 2), b["faces"], tuple(round(b["bbox"]["max"][k] - b["bbox"]["min"][k], 3) for k in range(3)))
    return shape, mount


def plate(key):
    """One plate: the number at the front, the mount behind it, both centred across the bed."""
    number, mount = os.path.join(ROOT, "stl", f"{key}.stl"), os.path.join(ROOT, "stl", "mount.stl")
    objects = []
    (nlo, nhi), (mlo, mhi) = bbox(number), bbox(mount)
    y0 = (BED - (nhi[1] - nlo[1]) - GAP - (mhi[1] - mlo[1])) / 2
    if (BED - (nhi[0] - nlo[0])) / 2 < 18 and y0 < 28:   # P1S excluded corner, 18 x 28 mm at the front left
        raise SystemExit(f"{key}: the number reaches the excluded corner")
    for k, (path, lo, hi, y) in enumerate([(number, nlo, nhi, y0), (mount, mlo, mhi, y0 + nhi[1] - nlo[1] + GAP)], start=1):
        objects.append({"path": path, "count": 1, "filaments": [1], "assemble_index": [k],
                        "pos_x": [float((BED - (hi[0] - lo[0])) / 2 - lo[0])], "pos_y": [float(y - lo[1])], "pos_z": [float(-lo[2])]})
    return {"plate_name": f"Key {key}", "need_arrange": False, "objects": objects}


def orca(out_path):
    settings = os.path.join(ROOT, "orca", "settings")
    json.dump({"plates": [plate(k) for k in build.KEYS]}, open(os.path.join(settings, "assemble.json"), "w"), indent=1)
    with tempfile.TemporaryDirectory() as out:
        r = subprocess.run(["orca-slicer", "--load-settings", "machine.json;process.json", "--load-filaments", "petg_hf_black.json",
                            "--load-assemble-list", "assemble.json", "--outputdir", out, "--export-3mf", "out.3mf"],
                           cwd=settings, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(os.path.join(out, "out.3mf")):
            raise SystemExit(f"orca-slicer failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
        shutil.move(os.path.join(out, "out.3mf"), out_path)
    os.remove(os.path.join(settings, "assemble.json"))
    for f in os.listdir(settings):
        if f.endswith(".log"):
            os.remove(os.path.join(settings, f))


def snapshot(key, out, view, script=None, size=(1200, 900)):
    """A snapshot of the key's design; script runs on top of the design first."""
    cmd = ["solidcraft-cli", "snapshot"]
    if script:
        path = os.path.join(WORK, f"snap_{os.getpid()}.json")
        json.dump({"commands": script}, open(path, "w"))
        cmd += [path, "--in"]
    cmd += [os.path.join(ROOT, "cad", f"{key}.solidcraft"), "--out", out, "--width", str(size[0]), "--height", str(size[1]), "--no-grid", "--no-axes"] + view
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def template(key, over):
    """templates/<key>.pdf: the number 1:1 on A4 landscape as seen from the front, with the screw
    holes marked, to tape to the wall and drill through; a 100 mm bar checks the print scale."""
    dpi = 25.4 / RES
    w, h = round(297 / RES), round(210 / RES)
    m, (ox, oy) = raster(key, over)
    page = Image.new("L", (w, h), 255)
    shape = Image.fromarray(np.where(m[::-1], 215, 255).astype(np.uint8))   # rows from the top
    x0, y0 = (w - shape.width) // 2, (h - shape.height) // 2
    page.paste(shape, (x0, y0))
    draw = ImageDraw.Draw(page)
    V = build.values(over)
    to_px = lambda x, y: (x0 + (x - ox) / RES, y0 + shape.height - (y - oy) / RES)
    r = 1.5 / RES
    for hy in ("hole_y1", "hole_y2"):
        cx, cy = to_px(V["mx"], V["my0"] + V[hy])
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=3)
        draw.line([cx - 3 * r, cy, cx + 3 * r, cy], fill=0, width=2)
        draw.line([cx, cy - 3 * r, cx, cy + 3 * r], fill=0, width=2)
    font = ImageFont.truetype(build.FONT, round(5 / RES))
    draw.text((round(10 / RES), round(8 / RES)), f"{key}: drill both crosses, 5 mm plugs, 3.5 mm screws. Print at 100 %.", fill=0, font=font)
    bar = (round(10 / RES), h - round(12 / RES))
    draw.line([bar, (bar[0] + round(100 / RES), bar[1])], fill=0, width=4)
    draw.text((bar[0], bar[1] - round(8 / RES)), "100 mm", fill=0, font=font)
    page.save(os.path.join(ROOT, "templates", f"{key}.pdf"), resolution=dpi)


def numbers_picture():
    """images/numbers.png: all numbers in black on white, two per row."""
    shots = []
    for key in build.KEYS:
        shot = os.path.join(WORK, f"front_{key}.png")
        snapshot(key, shot, ["--view", "top"], [{"command": "appearance.assign", "params": {"bodies": ["Number"], "color": "#000000"}}])
        subprocess.run(["magick", shot, "-alpha", "off", "-colorspace", "gray", "-threshold", "40%", "-trim", "+repage", "-resize", "x110", "-bordercolor", "white",
                        "-border", "25", "-gravity", "center", "-extent", "320x160", shot], check=True)
        shots.append(shot)
    rows = []
    for i in range(0, len(shots), 2):
        rows.append(os.path.join(WORK, f"row_{i}.png"))
        subprocess.run(["magick"] + shots[i:i + 2] + ["+append", rows[-1]], check=True)
    subprocess.run(["magick"] + rows + ["-append", os.path.join(ROOT, "images", "numbers.png")], check=True)


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    mounts = [export_key(key) for key in build.KEYS]
    if len({h for h, _ in mounts}) != 1:
        raise SystemExit("the mounts differ between the keys")
    shutil.copy(mounts[0][1], os.path.join(ROOT, "stl", "mount.stl"))
    orca(os.path.join(ROOT, "orca", "eMudhra_Keys.3mf"))
    numbers_picture()
