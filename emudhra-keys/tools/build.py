"""Generates the SolidCraft script for one wall number of a leaked eMudhra CA private key: the
key's digits as one solid piece, and the wall mount it hangs on. The mount is the same for every
key: a short dovetail rail held by two countersunk screws. Its plan narrows towards the top, so
the number wedges tight as it slides down and hangs without play, even off its centre of mass.
The slot hides behind the digits: a pocket in the number's back takes the rail, then the number
slides down until the rail wedges in the dovetail part above the pocket.

Usage: python -I build.py OUT.json KEY MX MY0 [JOIN…]
       MX, MY0: the rail's centre X and bottom Y on the number; JOIN: per pair of digits, how far
       their outlines overlap (mm); make.py finds them all
       (as a module: steps(key, over) gives the commands in named steps)

Coordinates: the number as it hangs, back on Z = 0 (its print orientation, front up), +Y up the
wall, the digits' outline centred on X = 0, the text's height on Y = 0. The mount lies seated in the slot (Z 0 … rail_h).
Bodies: "Number", "Mount".
"""
import json
import math
import os
import re
import sys

KEYS = [4, 56, 66, 115, 155, 156, 230, 237]   # the eight private keys, all below 256
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "NotoSans-Black.ttf")   # SIL Open Font License
FLANK = 20.0   # dovetail flank angle from vertical (deg)
TAPER = 3.0    # the rail's plan narrows by this angle on each side towards the top (deg)
# each digit's outline left and right of where the font centres it, per mm of text_h (measured)
INK = {"0": (-0.3613, 0.3613), "1": (-0.3529, 0.2339), "2": (-0.3796, 0.3571), "3": (-0.3627, 0.3529), "4": (-0.3866, 0.3894),
       "5": (-0.3459, 0.3459), "6": (-0.3627, 0.3669), "7": (-0.3571, 0.3641), "8": (-0.3641, 0.3655), "9": (-0.3669, 0.3627)}

P = {
    # number
    "text_h": ("115 mm", "digit height; 3 digits fill the 256 mm bed"),
    "num_t": ("10 mm", "thickness of the number"),
    # wall mount: a dovetail rail, its root on the wall
    "rail_l": ("21 mm", "rail length: the longest that fits inside 237"),
    "rail_w": ("11 mm", "rail width at the wall, at its bottom end"),
    "rail_h": ("4 mm", "rail height off the wall"),
    "hole_y1": ("4.5 mm", "lower screw hole above the rail's bottom end"),
    "hole_y2": ("16.5 mm", "upper screw hole above the rail's bottom end: 12 mm apart"),
    "hole_d": ("4 mm", "screw clearance hole, for 3.5 mm countersunk wood screws"),
    "cs_d": ("7.5 mm", "countersink diameter (90 degrees), for a 3.5 mm screw head of 7 mm"),
    # slot in the number
    "c": ("0.25 mm", "clearance of the pocket around the rail and above it (PETG)"),
    "e": ("3 mm", "room above the rail's top end: where it wedges shifts by 1 / (2 tan_t) per mm of slot width"),
    "wall_m": ("2.5 mm", "wall the slot keeps from the digits' edge at least (make.py)"),
    "mx": ("0 mm", "rail centre X on the number, set by make.py"),
    "my0": ("0 mm", "rail bottom end Y on the number when it hangs, set by make.py"),
    "ext": ("2 mm", "the rail's plan runs on this far before its ends are cut square"),
    "eps": ("0.5 mm", "overshoot of cuts"),
}


def derived():
    """Parameters fixed by FLANK and TAPER: the generator writes their numbers, as the expressions have no trig."""
    return {
        "tan_a": (f"{math.tan(math.radians(FLANK)):.6f}", f"tan of the flank angle ({FLANK:g} degrees from vertical)"),
        "tan_t": (f"{math.tan(math.radians(TAPER)):.6f}", f"tan of the plan taper ({TAPER:g} degrees each side)"),
        "pocket_w": ("rail_w + 2 * rail_h * tan_a + 2 * c", "pocket width: the rail's widest part plus clearance"),
    }


UNITLESS = {"tan_a", "tan_t"}


def params():
    return {**P, **derived()}


def ev(expr, V):
    """Numeric value (mm) of an expression over the parameters V."""
    e = re.sub(r"\b(mm|deg)\b", "", expr)
    return eval(e, {"__builtins__": {}, "sqrt": math.sqrt, "min": min}, V)


def values(over=None):
    V = {}
    for k, (e, _) in params().items():
        V[k] = ev((over or {}).get(k, e), V)
    return V


def footprint(V):
    """The slot's outline on the number's back relative to the rail's bottom centre, grown by the
    wall_m: (x0, x1, y0, y1). make.py fits it inside the digits."""
    hw = V["pocket_w"] / 2 + V["wall_m"]
    return -hw, hw, -V["rail_l"] - 2 * V["c"] - V["wall_m"], V["rail_l"] + V["e"] + V["wall_m"]


class Steps:
    def __init__(self):
        self.steps = []

    def step(self, name):
        self.steps.append((name, []))

    def add(self, command, **params):
        self.steps[-1][1].append({"command": command, "params": params})


def rail_half(y):
    """Half width of the rail's root at height y (expression)."""
    return f"rail_w / 2 - (({y}) - my0) * tan_t"


def plan(s, y0, y1, depth):
    """The rail's root plan from y0 to y1, each end run on by ext, narrowed by the flank as if
    `depth` below the root, as a closed polygon in the active sketch."""
    ya, yb = f"({y0}) - ext", f"({y1}) + ext"
    ha, hb = (f"({rail_half(y)}) - ({depth}) * tan_a" for y in (ya, yb))
    s.add("sketch.line", points=[[f"mx - ({ha})", ya], [f"mx + ({ha})", ya], [f"mx + ({hb})", yb], [f"mx - ({hb})", yb]],
          closed=True, infer=False)


def steps(key, over):
    """Named command steps for one key. over: parameter overrides; make.py sets mx, my0 and the
    joins, which have no default."""
    s = Steps()

    s.step("Parameters")
    for k, (e, comment) in params().items():
        s.add("parameters.add", name=k, expression=(over or {}).get(k, e), comment=comment, **({"unit": ""} if k in UNITLESS else {}))
    for i, k in enumerate(joins(key), start=1):
        s.add("parameters.add", name=k, expression=over[k], comment=f"digit {i} and {i + 1}'s outlines overlap this far (make.py)")

    s.step("Number")
    for c in number_commands(key):
        s.add(c["command"], **c["params"])

    # the dovetail part: the rail's own flanks (it wedges against them), e above its top end,
    # c deeper than the rail; started below the back so the cut ends in air. The tapered
    # extrude leans the ends too: the box cuts them square.
    s.step("Slot")
    s.add("sketch.create", plane="XY", offset="0 mm - eps")
    plan(s, "my0", "my0 + rail_l + e", "eps")
    s.add("sketch.finish")
    s.add("solid.extrude", distance="eps + rail_h + c", taper=f"{FLANK} deg", operation="new", body_name="Slot", name="Slot_dovetail")
    s.add("solid.box", length="pocket_w + 4 * ext", width="rail_l + e", height="rail_h + c + 3 * eps",
          corner=["mx - pocket_w / 2 - 2 * ext", "my0", "0 mm - 2 * eps"], operation="intersect", targets=["Slot"], name="Slot_ends")
    # the pocket below it takes the whole rail when the number goes onto the wall
    s.add("solid.box", length="pocket_w", width="rail_l + 2 * c + eps", height="2 * eps + rail_h + 2 * c",
          corner=["mx - pocket_w / 2", "my0 - rail_l - 2 * c", "0 mm - 2 * eps"], operation="new", body_name="Pocket", name="Pocket")
    s.add("solid.combine", target="Slot", tools=["Pocket"], operation="join")
    s.add("solid.combine", target="Number", tools=["Slot"], operation="cut")

    s.step("Mount")
    s.add("sketch.create", plane="XY")
    plan(s, "my0", "my0 + rail_l", "0 mm")
    s.add("sketch.finish")
    s.add("solid.extrude", distance="rail_h", taper=f"{FLANK} deg", operation="new", body_name="Mount", name="Rail")
    s.add("solid.box", length="pocket_w + 4 * ext", width="rail_l", height="rail_h + 2 * eps",
          corner=["mx - pocket_w / 2 - 2 * ext", "my0", "0 mm - eps"], operation="intersect", targets=["Mount"], name="Rail_ends")

    s.step("Screw holes")
    for y in ("hole_y1", "hole_y2"):
        s.add("solid.hole", position=["mx", f"my0 + {y}", "rail_h"], diameter="hole_d", type="countersink", cs_diameter="cs_d",
              cs_angle="90 deg", targets=["Mount"])

    s.add("appearance.assign", bodies=["Number", "Mount"], color="#1d1f22")
    return s.steps


def joins(key):
    """Names of the parameters by which each digit's outline overlaps the one before (join_1 is
    between the first and second digit); make.py sets them so each pair shares enough area."""
    return [f"join_{i}" for i in range(1, len(str(key)))]


def centres(key):
    """Where the font centres each digit (expressions): each outline overlaps the one before by its
    join_i, the whole outline centred on X = 0."""
    digits = str(key)
    xs = [0.0]
    for a, b in zip(digits, digits[1:]):
        xs.append(xs[-1] + INK[a][1] - INK[b][0])   # in text_h, before the overlaps
    mid = (xs[0] + INK[digits[0]][0] + xs[-1] + INK[digits[-1]][1]) / 2
    j = joins(key)
    half = " + ".join(j) or "0 mm"
    return [f"{x - mid:.6f} * text_h - ({' + '.join(j[:i]) or '0 mm'}) + ({half}) / 2" for i, x in enumerate(xs)]


def number_commands(key):
    """The digits as body "Number", one sketch and extrude per digit, each joined to the ones before
    (overlapping glyphs extruded together stay separate lumps)."""
    out = []
    for i, (d, x) in enumerate(zip(str(key), centres(key))):
        out += [
            {"command": "sketch.create", "params": {"plane": "XY"}},
            {"command": "sketch.text", "params": {"text": d, "at": [x, "0 mm - text_h / 2"], "height": "text_h", "font": FONT, "align": "center"}},
            {"command": "sketch.finish", "params": {}},
            {"command": "solid.extrude", "params": {"distance": "num_t", "name": f"Digit_{i + 1}",
                                                    **({"operation": "new", "body_name": "Number"} if i == 0 else {"operation": "join", "targets": ["Number"]})}},
        ]
    return out


def text_script(key, over):
    """Just the parameters and the digits, to measure them quickly."""
    return {"commands": steps(key, over)[0][1] + number_commands(key)}


def script(key, over):
    return {"commands": [c for _, cs in steps(key, over) for c in cs]}


def defects(result):
    """Problems in a `solidcraft-cli eval` result: timeline errors and warnings, rolled-back steps,
    booleans the kernel had to nudge or truncated, and bodies other than Number and Mount.
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
    if bodies != ["Mount", "Number"]:
        out.append(f"bodies {bodies}, expected Mount and Number")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 5 or len(sys.argv) != 5 + len(str(sys.argv[2])) - 1:
        raise SystemExit(__doc__)
    key, mx, my0 = int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    over = {"mx": f"{mx} mm", "my0": f"{my0} mm", **{k: f"{float(v)} mm" for k, v in zip(joins(key), sys.argv[5:])}}
    json.dump(script(key, over), open(sys.argv[1], "w"), indent=1)
