"""Rebuilds every print file from build.py: per label the parametric design cad/<label>.solidcraft,
the STLs of the bin and its text in stl/ and a one-bin project orca/bins/<label>.3mf, then
orca/Gridfinity_Bolt_Bins.3mf with all bins on one plate and the pictures in images/. In the 3MFs
each bin is one object of two parts: the bin on filament 1, the text on filament 2.

Stops with an error when a design has a kernel defect (build.defects), when a label's text does not
keep build.TEXT_CLEAR from the lip, or when OrcaSlicer fails.

Usage: python -I make.py   (from anywhere; needs solidcraft-cli and orca-slicer on the PATH)
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
GAP = 2.0           # mm between bins on the plate
ORIGIN = (20.0, 2.0)  # plate corner of the first bin, clear of the P1S excluded corner (18 x 28 mm)
COLUMNS = 5          # cells per row on the 256 mm bed, the prime tower beside them


def bbox_min(path):
    """Minimum corner of a binary STL."""
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    lo = [math.inf] * 3
    for i in range(n):
        v = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
        for k in range(9):
            lo[k % 3] = min(lo[k % 3], v[k])
    return lo


def stem(label):
    return label.replace(" ", "_")


def run(script, save=None):
    path = os.path.join(WORK, "script.json")
    json.dump(script, open(path, "w"))
    cmd = ["solidcraft-cli", "run", path, "--quiet"] + (["--save", save] if save else [])
    subprocess.run(cmd, check=True)


def evaluate(path):
    """`solidcraft-cli eval` of a script or design file."""
    out = os.path.join(WORK, "eval.json")
    subprocess.run(["solidcraft-cli", "eval", path, "--json-out", out], check=True, stdout=subprocess.DEVNULL)
    return json.load(open(out))


def text_box(label, cx, text=None):
    """Outline (min, max) of the label's text body."""
    path = os.path.join(WORK, "text.json")
    json.dump(build.text_script(label, cx, text), open(path, "w"))
    b = next(b for b in evaluate(path)["bodies"] if b["name"] == "Label")["bbox"]
    return b["min"], b["max"]


def fit_text(label, cx):
    """Text overrides that centre the text on the ledge by its measured outline, shrinking the
    capital height only when the text would come nearer than TEXT_CLEAR to the lip."""
    V = build.values(cx, 1)
    c = build.TEXT_CLEAR
    target = (V["text_x"], V["D"] / 2 - V["wall_t"] - V["ledge_d"] / 2)
    half_w = min(target[0] - (-V["W"] / 2 + V["lip_in"] + c), V["W"] / 2 - V["lip_in"] - c - target[0])
    half_h = min(V["D"] / 2 - V["lip_in"] - c - target[1], target[1] - (V["D"] / 2 - V["wall_t"] - V["ledge_d"] + c))
    lo, hi = text_box(label, cx)
    scale = min(1.0, 2 * half_w / (hi[0] - lo[0]), 2 * half_h / (hi[1] - lo[1]))
    h = math.floor(V["text_h"] * scale * 100) / 100
    lo, hi = text_box(label, cx, {"text_h": f"{h} mm"})
    dx, dy = target[0] - (lo[0] + hi[0]) / 2, target[1] - (lo[1] + hi[1]) / 2
    return {"text_h": f"{h} mm", "text_dx": f"{dx:.4f} mm", "text_dy": f"{dy:.4f} mm"}, target, (half_w, half_h)


def export_bin(label):
    """The label's design, checked, and its two STLs. Returns its cell count."""
    cx = build.cells_for(label)
    text, target, (half_w, half_h) = fit_text(label, cx)
    d = build.script(label, cx, text=text)
    for body, suffix in (("Bin", ""), ("Label", "_text")):
        d["commands"].append({"command": "file.export",
                              "params": {"path": os.path.join(ROOT, "stl", f"{stem(label)}{suffix}.stl"), "bodies": [body]}})
    design = os.path.join(ROOT, "cad", f"{stem(label)}.solidcraft")
    run(d, save=design)
    result = evaluate(design)
    problems = build.defects(result)
    b = next(b for b in result["bodies"] if b["name"] == "Label")["bbox"]
    centre = [(b["min"][k] + b["max"][k]) / 2 for k in (0, 1)]
    if max(abs(centre[0] - target[0]), abs(centre[1] - target[1])) > 0.01:
        problems.append(f"text centre {centre} is not {target}")
    if (b["max"][0] - b["min"][0]) / 2 > half_w + 1e-6 or (b["max"][1] - b["min"][1]) / 2 > half_h + 1e-6:
        problems.append(f"text {b} closer than {build.TEXT_CLEAR} mm to the lip")
    if problems:
        raise SystemExit(f"{label}: " + "; ".join(problems))
    print(f"{label}: 1x{cx}, text {text['text_h']}, eval clean", flush=True)
    return cx


def layout(bins):
    """Rows of COLUMNS cells, wide bins first; returns [(label, cells, x_min, y_min)]."""
    pitch = 41.5 + GAP
    placed, row, col = [], 0, 0
    for label, cx in sorted(bins, key=lambda b: -b[1]):
        if col + cx > COLUMNS:
            row, col = row + 1, 0
        placed.append((label, cx, ORIGIN[0] + col * pitch, ORIGIN[1] + row * pitch))
        col += cx
    return placed


def orca(placed, out_path, plate_name):
    """A 3MF of the placed bins [(label, cells, x_min, y_min)]: each bin one object of two parts,
    the bin on filament 1 and its text on filament 2."""
    objects = []
    for k, (label, cx, x, y) in enumerate(placed, start=1):   # parts of one assemble_index form one object; 0 does not group
        paths = [os.path.join(ROOT, "stl", f"{stem(label)}{suffix}.stl") for suffix in ("", "_text")]
        lo = bbox_min(paths[0])
        for path, fil in zip(paths, (1, 2)):
            # pos moves the STL's own coordinates; both parts share the bin's frame, so the same move
            objects.append({"path": path, "count": 1, "filaments": [fil], "assemble_index": [k],
                            "pos_x": [x - lo[0]], "pos_y": [y - lo[1]], "pos_z": [-lo[2]]})
    plate = {"plate_name": plate_name, "need_arrange": False, "objects": objects}
    settings = os.path.join(ROOT, "orca", "settings")
    json.dump({"plates": [plate]}, open(os.path.join(settings, "assemble.json"), "w"), indent=1)
    with tempfile.TemporaryDirectory() as out:
        r = subprocess.run(["orca-slicer", "--load-settings", "machine.json;process.json", "--load-filaments", "pla_grey.json;pla_white.json",
                            "--load-assemble-list", "assemble.json", "--outputdir", out, "--export-3mf", "out.3mf"],
                           cwd=settings, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(os.path.join(out, "out.3mf")):
            raise SystemExit(f"orca-slicer failed for {out_path} ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
        shutil.move(os.path.join(out, "out.3mf"), out_path)
    os.remove(os.path.join(settings, "assemble.json"))
    for f in os.listdir(settings):
        if f.endswith(".log"):
            os.remove(os.path.join(settings, f))


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "orca", "bins"), exist_ok=True)
    bins = [(label, export_bin(label)) for label in build.LABELS]
    for label, cx in bins:
        w = cx * 42 - 0.5
        orca([(label, cx, (256 - w) / 2, (256 - 41.5) / 2)], os.path.join(ROOT, "orca", "bins", f"{stem(label)}.3mf"), label)
    orca(layout(bins), os.path.join(ROOT, "orca", "Gridfinity_Bolt_Bins.3mf"), "Gridfinity Bolt Bins")
    for label, name in (("M5x10", "bin_1x1"), ("M5x30", "bin_1x2")):
        shot = os.path.join(WORK, f"{name}.png")
        subprocess.run(["solidcraft-cli", "snapshot", os.path.join(ROOT, "cad", f"{stem(label)}.solidcraft"), "--out", shot,
                        "--width", "1200", "--height", "900", "--view", "iso", "--no-grid", "--no-axes"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["magick", shot, "-trim", "-resize", "700x", os.path.join(ROOT, "images", f"{name}.png")], check=True)
