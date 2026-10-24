"""Generates the SolidCraft script for a labelled Gridfinity bin for bolts, modelled after the
"Complete Metric Bolts M3,4,5,6 LABELED Gridfinity" bins (MakerWorld 946272) Louis already uses:
5 units high with a stacking lip, a finger scoop at the front, a label ledge at the back with raised
text for a second colour, and Gridfinity Refined slot-in magnet pockets (6 x 2 mm magnets).

Usage: python -I build.py OUT.json [--label TEXT] [--cells X Y] [--no-magnets]
       (as a module: steps(label, cx, cy, magnets) gives the commands in named steps)

Coordinates: bin centred on X/Y = 0, Z up from the bottom of the feet. Front (scoop) is -Y,
back (label ledge) is +Y; the text reads along +X. Body "Bin" is the bin, body "Label" the text.

Every length is a user parameter or an expression of user parameters. Numbers marked "original"
were measured on the mesh of the MakerWorld bin; the rest follow the Gridfinity spec as
gridfinity-rebuilt-openscad implements it.
"""
import json
import math
import re
import sys

P = {
    # grid
    "pitch": ("42 mm", "Gridfinity grid pitch"),
    "gap": ("0.5 mm", "clearance between neighbouring bins"),
    "cx": ("1", "cells along X (width)"),
    "cy": ("1", "cells along Y (depth)"),
    "W": ("cx * pitch - gap", "outer width"),
    "D": ("cy * pitch - gap", "outer depth"),
    "r_out": ("3.75 mm", "outer corner radius"),
    "u": ("7 mm", "Gridfinity height unit"),
    "units": ("5", "bin height in units, incl. the base, without the lip"),
    "H": ("units * u", "top of the walls = bottom of the stacking lip"),
    # foot of each cell, bottom to top: 45 degrees out, vertical, 45 degrees out
    "f1": ("0.8 mm", "foot: lower 45 degree step"),
    "f2": ("1.8 mm", "foot: vertical part"),
    "f3": ("2.15 mm", "foot: upper 45 degree step"),
    "foot_h": ("f1 + f2 + f3", "foot height"),
    "cell": ("pitch - gap", "foot width at its top"),
    # walls and floor
    "wall_t": ("0.96 mm", "wall thickness (original)"),
    "floor_z": ("6.95 mm", "cavity floor above the bottom (original)"),
    "floor_r": ("2.7 mm", "rounding between floor and side and back walls (original)"),
    "front_t": ("2.35 mm", "front wall above the scoop (original)"),
    "scoop_r": ("15 mm", "finger scoop reaches this far up the front wall and along the floor (original)"),
    "scoop_k": ("1.5 mm", "scoop arc's centre this much nearer floor and wall than a tangent one, so it meets them at atan(k / (r - k)) = 6 degrees (tangent, the kernel nudges the cut)"),
    # stacking lip, from the lip bottom up: 45 degrees out, vertical, 45 degrees out to the tip
    "sup_h": ("1.2 mm", "vertical support below the lip"),
    "lip_a": ("0.7 mm", "lip: lower 45 degree step"),
    "lip_b": ("1.8 mm", "lip: vertical part"),
    "lip_c": ("1.9 mm", "lip: upper 45 degree step to the outer edge"),
    "lip_in": ("lip_a + lip_c", "inset of the lip's inner face at its bottom"),
    "tip_cut": ("0.85 mm", "the tip is flattened this much (its rounding, original top at 38.55 mm)"),
    "top": ("H + lip_a + lip_b + lip_c - tip_cut", "overall height"),
    "tip_r": ("0.6 mm", "rounding of the lip's outer top edge"),
    # label ledge at the back
    "ledge_z": ("H - 0.2 mm", "ledge top, one layer below the lip (original: at H; flush with the lip's edge the kernel nudges the cut)"),
    "ledge_d": ("13.85 mm", "ledge depth from the back wall (original)"),
    "ledge_t": ("1.2 mm", "height of the ledge's front face (original)"),
    "ledge_a": ("36 deg", "ledge underside slope from horizontal (original; 54 degrees from vertical)"),
    "ledge_r": ("2 mm", "rounding where the ledge's underside meets the back wall"),
    "text_h": ("7.5 mm", "capital height of the label (make.py shrinks it where a label would come nearer than text_clear to the lip)"),
    "text_x": ("0 mm - (cx - 1) / 2 * pitch", "text centre: over the first cell"),
    "text_y": ("D / 2 - wall_t - ledge_d / 2 - text_h / 2", "text baseline: capitals centred on the ledge"),
    "text_dx": ("0 mm", "text shift along X, set by make.py so the text's measured outline is centred"),
    "text_dy": ("0 mm", "text shift along Y, set by make.py so the text's measured outline is centred"),
    "text_t": ("1 mm", "raised height of the label (5 layers of 0.2 mm)"),
    # Gridfinity Refined magnet pockets: a bore with a slot to the side, the magnet slides in
    "mag_d": ("5.86 mm", "magnet pocket width, press fit for a 6 mm magnet (gridfinity-rebuilt-openscad holes.scad, Refined holes)"),
    "mag_h": ("1.9 mm", "magnet pocket height (2 mm magnet)"),
    "mag_z": ("0.4 mm", "material under the magnet pocket"),
    "mag_off": ("13 mm", "magnet centre from the cell centre along X and Y"),
    "poke_d": ("2.5 mm", "width of the slot to push the magnet out (original)"),
    "poke_s": ("2.53 mm", "push-out slot starts this far inwards from the magnet centre (original)"),
    "poke_l": ("8.18 mm", "push-out slot reaches this far inwards from the magnet centre (original)"),
    "eps": ("0.5 mm", "overshoot of cuts and overlap of joins"),
}

# the bins this set adds: M5 and M6 screws up to 30 mm, and heat-set inserts (HSI) M3 to M6
LABELS = [f"M{d}x{n}" for d in (5, 6) for n in (8, 10, 12, 14, 16, 18, 20, 25, 30)] + [f"M{d} HSI" for d in (3, 4, 5, 6)]
TEXT_CLEAR = 1.0    # mm the text keeps from the lip's inner faces
SCREW_CLEAR = 2.0   # mm a lying screw needs beyond its overall length


def usable(cx):
    """Flat floor length along X of a bin cx cells wide (between the floor roundings), in mm."""
    V = values(cx, 1)
    return V["W"] - 2 * V["wall_t"] - 2 * V["floor_r"]


def cells_for(label):
    """Cells along X a label needs: a socket head screw (ISO 4762, head height = d) lies flat on
    the floor along X, so length + d + SCREW_CLEAR must fit the flat floor. Other labels: 1."""
    m = re.fullmatch(r"M(\d+)x(\d+)", label)
    if not m:
        return 1
    need = int(m.group(2)) + int(m.group(1)) + SCREW_CLEAR
    for cx in (1, 2, 3):
        if need <= usable(cx):
            return cx
    raise ValueError(f"{label}: {need} mm does not fit 3 cells")


def shown(label):
    """Label text as the originals print it: a space pads one-digit lengths (M5x 8)."""
    m = re.fullmatch(r"(M\d+x)(\d)", label)
    return f"{m.group(1)} {m.group(2)}" if m else label

XY = "XY"
YZ = {"origin": [0, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (Y, Z), normal +X


def ev(expr, V):
    """Numeric value (mm, or degrees for angles) of an expression over the parameters V."""
    e = re.sub(r"\b(mm|deg)\b", "", expr)
    return eval(e, {"__builtins__": {}, "sqrt": math.sqrt, "min": min}, V)


def values(cx, cy):
    V = {}
    for k, (e, _) in P.items():
        V[k] = ev({"cx": str(cx), "cy": str(cy)}.get(k, e), V)
    return V


class Steps:
    def __init__(self):
        self.steps = []

    def step(self, name):
        self.steps.append((name, []))

    def add(self, command, **params):
        self.steps[-1][1].append({"command": command, "params": params})


def rrect(s, x0, y0, x1, y1, r):
    """Closed rounded rectangle in the active sketch (expressions); first line id must be l1."""
    s.add("sketch.line", points=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], closed=True, infer=False)
    s.add("sketch.fillet", points=["l1.end", "l2.end", "l3.end", "l4.end"], radius=r)


def oblong(s, x, y, dx, dy, length, width, round_start, round_end):
    """Closed slot in the active sketch from (x, y) along the axis direction (dx, dy) for length,
    width wide; either end flat or a half circle centred on it (expressions)."""
    nx, ny = -dy, dx
    h = f"({width}) / 2"
    pt = lambda bx, by, k, m: [f"{bx} + ({k}) * ({length}) * {dx} + ({m}) * {h} * {nx}",
                               f"{by} + ({k}) * ({length}) * {dy} + ({m}) * {h} * {ny}"]
    s0, s1, e0, e1 = pt(x, y, 0, -1), pt(x, y, 0, 1), pt(x, y, 1, -1), pt(x, y, 1, 1)
    e = pt(x, y, 1, 0)
    if round_end:
        s.add("sketch.line", points=[s0, e0], infer=False)
        s.add("sketch.arc.center_point", center=e, start=e0, end=e1)
        chain = [e1, s1]
    else:
        chain = [s0, e0, e1, s1]
    if round_start:
        s.add("sketch.line", points=chain, infer=False)
        s.add("sketch.arc.center_point", center=[x, y], start=s1, end=s0)
    else:
        s.add("sketch.line", points=chain + ([s0] if round_end else []), closed=not round_end, infer=False)


def cells(cx, cy):
    """Cell centres as expressions."""
    return [(f"({i} - (cx - 1) / 2) * pitch", f"({j} - (cy - 1) / 2) * pitch") for i in range(cx) for j in range(cy)]


def steps(label, cx=1, cy=1, magnets=True, text=None):
    """Named command steps for one bin. text: overrides for text_h, text_dx, text_dy (expressions)."""
    over = {"cx": str(cx), "cy": str(cy), **(text or {})}
    V = values(cx, cy)
    s = Steps()

    s.step("Parameter")
    for k, (e, c) in P.items():
        e = over.get(k, e)
        unit = {"cx": "", "cy": "", "units": ""}.get(k)
        s.add("parameters.add", name=k, expression=e, comment=c, **({"unit": unit} if unit is not None else {}))

    # each cell's foot: tapered steps grown from its bottom face
    s.step("Fuesse")
    for n, (x, y) in enumerate(cells(cx, cy)):
        s.add("sketch.create", plane=XY)
        h = "cell / 2 - f1 - f3"
        rrect(s, f"{x} - ({h})", f"{y} - ({h})", f"{x} + {h}", f"{y} + {h}", "r_out - f1 - f3")
        s.add("sketch.finish")
        # each foot its own body, joined by the body above them (joining a tapered foot to another body leaves slivers)
        body = "Bin" if n == 0 else f"Fuss_{n + 1}"
        s.add("solid.extrude", distance="f1", taper="45 deg", operation="new", body_name=body, name=f"Fuss_{n + 1}_unten")
        fx, fy = ev(x, V), ev(y, V)
        s.add("solid.extrude", face=[fx, fy, V["f1"]], face_body=body, distance="f2", operation="join", targets=[body], name=f"Fuss_{n + 1}_mitte")
        s.add("solid.extrude", face=[fx, fy, V["f1"] + V["f2"]], face_body=body, distance="f3", taper="45 deg", operation="join",
              targets=[body], name=f"Fuss_{n + 1}_oben")

    s.step("Koerper")
    s.add("sketch.create", plane=XY, offset="foot_h")
    rrect(s, "-W / 2", "-D / 2", "W / 2", "D / 2", "r_out")
    s.add("sketch.finish")
    s.add("solid.extrude", distance="top - foot_h", operation="join", targets=["Bin"], name="Koerper")
    if cx * cy > 1:
        s.add("solid.combine", target="Bin", tools=[f"Fuss_{n + 1}" for n in range(1, cx * cy)], operation="join")

    # the cavity as a tool body: walls, lip support and lip in tapered steps
    s.step("Innenraum")
    s.add("sketch.create", plane=XY, offset="floor_z")
    rrect(s, "-W / 2 + wall_t", "-D / 2 + wall_t", "W / 2 - wall_t", "D / 2 - wall_t", "r_out - wall_t")
    s.add("sketch.finish")
    z1 = "H - sup_h - (lip_in - wall_t)"
    s.add("solid.extrude", distance=f"{z1} - floor_z", operation="new", body_name="Tasche", name="Tasche_Wand")
    zs = [
        (z1, "lip_in - wall_t", "-45 deg", "Tasche_Stuetze"),
        ("H - sup_h", "sup_h", None, "Tasche_Stuetze_senkrecht"),
        ("H", "lip_a", "45 deg", "Tasche_Lippe_unten"),
        ("H + lip_a", "lip_b", None, "Tasche_Lippe_mitte"),
        ("H + lip_a + lip_b", "lip_c - tip_cut + eps", "45 deg", "Tasche_Lippe_oben"),   # runs through the top
    ]
    for z, dist, taper, name in zs:
        p = {"face": [0, 0, round(ev(z, V), 6)], "face_body": "Tasche", "distance": dist, "operation": "join", "targets": ["Tasche"], "name": name}
        if taper:
            p["taper"] = taper
        s.add("solid.extrude", **p)

    # the label ledge stays: cut it out of the tool, then the tool out of the bin
    s.step("Etikettenleiste")
    yf = "D / 2 - wall_t - ledge_d"
    yb = "D / 2 + eps"
    drop = f"(({yb}) - ({yf})) * tan_a"
    s.add("parameters.add", name="tan_a", expression=f"{math.tan(math.radians(V['ledge_a'])):.6f}",
          unit="", comment="tan(ledge_a), kept in step with ledge_a by build.py")
    s.add("sketch.create", plane=YZ)
    s.add("sketch.line", points=[[yf, "ledge_z"], [yb, "ledge_z"], [yb, f"ledge_z - ledge_t - {drop}"], [yf, "ledge_z - ledge_t"]], closed=True, infer=False)
    s.add("sketch.finish")
    s.add("solid.extrude", distance="W + 2 * eps", direction="symmetric", operation="new", body_name="Leiste", name="Leiste")
    s.add("solid.combine", target="Tasche", tools=["Leiste"], operation="cut")
    # finger scoop: the region outside a circle in the front bottom corner stays too
    s.step("Griffmulde")
    # front wall thickened to front_t up to the lip support, the scoop rounding from it to the floor
    yf = "-D / 2 + front_t"
    yc, zc = f"{yf} + scoop_r - scoop_k", "floor_z + scoop_r - scoop_k"
    rad = "sqrt((scoop_r - scoop_k) * (scoop_r - scoop_k) + scoop_k * scoop_k)"
    zw, zt = "floor_z + scoop_r", "H - sup_h / 2"
    bottom = [yc, f"{zc} - {rad}"]
    zb = f"{zc} - {rad} - eps"
    s.add("sketch.create", plane=YZ)
    s.add("sketch.line", points=[bottom, [yc, zb], ["-D / 2 - eps", zb], ["-D / 2 - eps", zt], [yf, zt], [yf, zw]], infer=False)
    s.add("sketch.arc.center_point", center=[yc, zc], start=[yf, zw], end=bottom)
    s.add("sketch.finish")
    s.add("solid.extrude", distance="W + 2 * eps", direction="symmetric", operation="new", body_name="Mulde", name="Griffmulde",
          profiles=[{"point": [-V["D"] / 2, V["floor_z"]]}])
    s.add("solid.combine", target="Tasche", tools=["Mulde"], operation="cut")
    s.step("Aushoehlen")
    s.add("solid.combine", target="Bin", tools=["Tasche"], operation="cut")

    if magnets:
        # pinwheel: each pocket opens to the nearest side, turning round the cell; a narrow slot
        # through the bottom runs inwards from it, to push the magnet out with a pin
        dirs = [((-1, 1), (0, 1)), ((1, 1), (1, 0)), ((1, -1), (0, -1)), ((-1, -1), (-1, 0))]
        pockets = [(f"{x} + ({sx}) * mag_off", f"{y} + ({sy}) * mag_off", dx, dy)
                   for x, y in cells(cx, cy) for (sx, sy), (dx, dy) in dirs]
        s.step("Magnete")
        s.add("sketch.create", plane=XY, offset="mag_z")
        for mx, my, dx, dy in pockets:
            oblong(s, mx, my, dx, dy, "pitch / 2 - mag_off + eps", "mag_d", round_start=True, round_end=False)
        s.add("sketch.finish")
        s.add("solid.extrude", distance="mag_h", operation="cut", targets=["Bin"], profiles="all", name="Magnettaschen")
        s.add("sketch.create", plane=XY, offset="0 mm - eps")
        for mx, my, dx, dy in pockets:
            oblong(s, f"{mx} - ({dx}) * poke_s", f"{my} - ({dy}) * poke_s", -dx, -dy, "poke_l - poke_s", "poke_d", round_start=False, round_end=True)
        s.add("sketch.finish")
        s.add("solid.extrude", distance="eps + mag_z + mag_h / 2", operation="cut", targets=["Bin"], profiles="all", name="Ausdrueckschlitze")

    # roundings no sketch can carry
    s.step("Rundungen")
    fz = V["floor_z"]
    xw = V["W"] / 2 - V["wall_t"]
    s.add("solid.fillet", body="Bin", radius="floor_r", edges=[[xw, 0, fz], [-xw, 0, fz], [0, V["D"] / 2 - V["wall_t"], fz]], name="Boden")
    yb_in = V["D"] / 2 - V["wall_t"]
    z_ledge = V["ledge_z"] - V["ledge_t"] - (yb_in - (V["D"] / 2 - V["wall_t"] - V["ledge_d"])) * math.tan(math.radians(V["ledge_a"]))
    s.add("solid.fillet", body="Bin", radius="ledge_r", edges=[[0, yb_in, z_ledge]], name="Leiste_Fuss")
    s.add("solid.fillet", body="Bin", radius="tip_r", edges=[[0, -V["D"] / 2, V["top"]]], name="Lippe_Spitze")

    s.step("Beschriftung")
    for c in label_commands(label):
        s.add(c["command"], **c["params"])
    s.add("appearance.assign", bodies=["Label"], color="#f2f2f2")
    s.add("appearance.assign", bodies=["Bin"], color="#8c8f94")
    return s.steps


def label_commands(label):
    """The raised text on the ledge as body "Label", centred over the first cell."""
    return [
        {"command": "sketch.create", "params": {"plane": XY, "offset": "ledge_z"}},
        {"command": "sketch.text", "params": {"text": shown(label), "at": ["text_x + text_dx", "text_y + text_dy"], "height": "text_h",
                                              "font": "Noto Sans", "bold": True, "align": "center"}},
        {"command": "sketch.finish", "params": {}},
        {"command": "solid.extrude", "params": {"distance": "text_t", "operation": "new", "body_name": "Label", "profiles": "all", "name": "Beschriftung"}},
    ] + ([] if len(glyphs(label)) < 2 else [
        # every glyph comes out as its own body; make.py checks that no other body is left
        {"command": "solid.combine", "params": {"target": "Label", "tools": [f"Label ({k})" for k in range(2, len(glyphs(label)) + 1)], "operation": "join"}}])


def glyphs(label):
    """Glyphs of the shown text that come out as separate pieces (the labels have no dotted letters)."""
    return shown(label).replace(" ", "")


def text_script(label, cx, text=None):
    """Just the parameters and the text, to measure the text's outline quickly."""
    st = steps(label, cx, 1, True, text)
    return {"commands": st[0][1] + label_commands(label)}


def script(label, cx=1, cy=1, magnets=True, text=None):
    return {"commands": [c for _, cs in steps(label, cx, cy, magnets, text) for c in cs]}


def defects(result):
    """Problems in a `solidcraft-cli eval` result: timeline errors and warnings, rolled-back steps,
    booleans the kernel had to nudge or truncated, and bodies other than Bin and Label.
    Empty when the design is clean."""
    out = []
    for t in result["timeline"]:
        name = t.get("name") or t.get("command")
        for key in ("error", "errors", "warnings", "warning", "rolled_back"):
            if t.get(key):
                out.append(f"{name}: {key} {t[key]}")
        diagnostics = t.get("boolean_diagnostics") or {}
        if diagnostics.get("truncated"):
            out.append(f"{name}: boolean diagnostics truncated")
        for e in diagnostics.get("events") or []:
            if e.get("strategy") not in ("refined_tolerance", "planar_fallback"):
                out.append(f"{name}: boolean {e.get('strategy')}")
    bodies = sorted(b["name"] for b in result["bodies"])
    if bodies != ["Bin", "Label"]:
        out.append(f"bodies {bodies}, expected Bin and Label")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    label, cx, cy, magnets = "M5x10", None, 1, True
    if "--label" in args:
        i = args.index("--label"); label = args[i + 1]; del args[i:i + 2]
    if "--cells" in args:
        i = args.index("--cells"); cx, cy = int(args[i + 1]), int(args[i + 2]); del args[i:i + 3]
    if "--no-magnets" in args:
        args.remove("--no-magnets"); magnets = False
    if len(args) != 1:
        raise SystemExit(__doc__)
    json.dump(script(label, cx or cells_for(label), cy, magnets), open(args[0], "w"), indent=1)
