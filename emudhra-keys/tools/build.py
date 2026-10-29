"""Generates the SolidCraft script for one wall sign of a leaked eMudhra CA private key: a plaque
with the key's number raised on its front (second colour), and the wall mount it slides onto.
The mount is the same for every key: a plate held by two countersunk screws, with a dovetail rail
running up the wall. The plaque has the matching slot in its back, open at the bottom and closed
at the top: lowered onto the rail, it rests on the rail's top end.

Usage: python -I build.py OUT.json KEY
       (as a module: steps(key) gives the commands in named steps)

Coordinates: the assembly as it hangs. The plaque's back lies on Z = 0 (its print orientation,
front up), +Y points up the wall, the plaque is centred on X/Y = 0. The mount lies behind it
(Z < 0), its rail reaching into the slot, centred on the plaque when hanging.
Bodies: "Plaque", "Number" (the raised digits), "Mount".
"""
import json
import math
import re
import sys

KEYS = [4, 56, 66, 115, 155, 156, 230, 237]   # the eight private keys, all below 256
FONT = "JetBrainsMono Nerd Font"   # its bold face; installed on this machine
DT_ANGLE = 30.0   # dovetail flank angle from vertical (deg); build.py derives tan_a and sec_a from it

P = {
    # plaque
    "digits": ("1", "number of digits"),
    "digit_w": ("58 mm", "plaque width per digit (the font's advance at text_h, measured)"),
    "pad": ("15 mm", "plaque width beyond the digits on each side"),
    "plaque_w": ("digits * digit_w + 2 * pad", "plaque width"),
    "plaque_h": ("120 mm", "plaque height, the same for every key"),
    "plaque_t": ("9 mm", "plaque thickness"),
    "plaque_r": ("10 mm", "plaque corner radius"),
    "edge_r": ("2 mm", "rounding of the plaque's front edge"),
    "text_h": ("70 mm", "digit height"),
    "text_t": ("1.6 mm", "raised height of the digits (8 layers of 0.2 mm)"),
    "text_dx": ("0 mm", "digit shift along X, set by make.py so their measured outline is centred"),
    "text_dy": ("0 mm", "digit shift along Y, set by make.py so their measured outline is centred"),
    # wall mount
    "plate_w": ("60 mm", "mount plate width"),
    "plate_h": ("50 mm", "mount plate height = rail length"),
    "plate_t": ("5 mm", "mount plate thickness"),
    "plate_r": ("5 mm", "mount plate corner radius"),
    "rail_w": ("14 mm", "rail width at its root"),
    "rail_h": ("5 mm", "rail height above the plate"),
    "root_r": ("1 mm", "rounding where the rail leaves the plate"),
    "hole_dx": ("20 mm", "screw hole centre from the middle"),
    "hole_d": ("4.5 mm", "screw clearance hole, for 4 mm countersunk wood screws"),
    "cs_d": ("8.5 mm", "countersink diameter (90 degrees), for a 4 mm screw head of 8 mm"),
    # joint
    "c": ("0.25 mm", "clearance of the slot to the rail, square to every face (PETG)"),
    "eps": ("0.5 mm", "overshoot of cuts"),
}


def derived():
    """Parameters fixed by DT_ANGLE: the generator writes their numbers, as the expressions have no trig."""
    a = math.radians(DT_ANGLE)
    return {
        "tan_a": (f"{math.tan(a):.6f}", f"tan of the dovetail flank angle ({DT_ANGLE:g} degrees from vertical)"),
        "sec_a": (f"{1 / math.cos(a):.6f}", "1 / cos of the flank angle"),
        "sin_a": (f"{math.sin(a):.6f}", "sin of the flank angle"),
        "cos_a": (f"{math.cos(a):.6f}", "cos of the flank angle"),
        # a rounding of root_r in the corner of angle 90 - a between plate and flank touches both this far from the corner
        "root_t": (f"root_r * {1 / math.tan(math.radians(90 - DT_ANGLE) / 2):.6f}", "rail root rounding: tangent length"),
        "mouth": ("root_t + 2 * c", "slot mouth chamfer, clears the rail's root rounding along both faces"),
    }


UNITLESS = {"digits", "tan_a", "sec_a", "sin_a", "cos_a"}
XZ = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (X, Z), normal -Y


def params():
    return {**P, **derived()}


def ev(expr, V):
    """Numeric value (mm) of an expression over the parameters V."""
    e = re.sub(r"\b(mm|deg)\b", "", expr)
    return eval(e, {"__builtins__": {}, "sqrt": math.sqrt, "min": min}, V)


def values(key, text=None):
    over = {"digits": str(len(str(key))), **(text or {})}
    V = {}
    for k, (e, _) in params().items():
        V[k] = ev(over.get(k, e), V)
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


def mirrored(half):
    """Closed polygon from its right half [(x, y)…] listed bottom to top, mirrored to the left."""
    return half + [[f"0 mm - ({x})", y] for x, y in reversed(half)]


def steps(key, text=None):
    """Named command steps for one key's plaque and the mount. text: overrides for text_dx, text_dy."""
    over = {"digits": str(len(str(key))), **(text or {})}
    V = values(key, text)
    s = Steps()

    s.step("Parameters")
    for k, (e, comment) in params().items():
        s.add("parameters.add", name=k, expression=over.get(k, e), comment=comment, **({"unit": ""} if k in UNITLESS else {}))

    s.step("Plaque")
    s.add("sketch.create", plane="XY")
    rrect(s, "0 mm - plaque_w / 2", "0 mm - plaque_h / 2", "plaque_w / 2", "plaque_h / 2", "plaque_r")
    s.add("sketch.finish")
    s.add("solid.extrude", distance="plaque_t", operation="new", body_name="Plaque", name="Plaque")

    # the slot: the rail's section offset by c, with a chamfered mouth that clears the rail's root rounding;
    # from below the plaque up to where the rail's top rests when the mount is centred
    s.step("Slot")
    a = "rail_w / 2 + c * sec_a"   # half width of the slot at the plaque's back
    s.add("sketch.create", plane=XZ)
    s.add("sketch.line", points=mirrored([
        [f"{a} + mouth", "0 mm - eps"],
        [f"{a} + mouth", "0 mm"],
        [f"{a} + mouth * sin_a", "mouth * cos_a"],
        [f"{a} + (rail_h + c) * tan_a", "rail_h + c"],
    ]), closed=True, infer=False)
    s.add("sketch.finish")
    # the sketch normal is -Y: direction negative runs along +Y from start_offset (along -Y)
    s.add("solid.extrude", distance="plaque_h / 2 + eps + plate_h / 2", direction="negative", start_offset="plaque_h / 2 + eps",
          operation="cut", targets=["Plaque"], name="Slot")

    s.step("Edge")
    x, y, r, z = V["plaque_w"] / 2, V["plaque_h"] / 2, V["plaque_r"], V["plaque_t"]
    k = r * (1 - math.cos(math.pi / 4))
    edges = [[0, y, z], [0, -y, z], [x, 0, z], [-x, 0, z]] + [[sx * (x - k), sy * (y - k), z] for sx in (1, -1) for sy in (1, -1)]
    s.add("solid.fillet", body="Plaque", radius="edge_r", edges=edges, name="Front_edge")

    s.step("Number")
    for c in number_commands(key):
        s.add(c["command"], **c["params"])

    # the mount as one section (plate and rail with its root roundings) along the rail
    s.step("Mount")
    s.add("sketch.create", plane=XZ)
    s.add("sketch.line", points=mirrored([
        ["plate_w / 2", "0 mm - plate_t"],
        ["plate_w / 2", "0 mm"],
        ["rail_w / 2", "0 mm"],
        ["rail_w / 2 + rail_h * tan_a", "rail_h"],
    ]), closed=True, infer=False)
    # polygon vertices v1…v8; line n ends at v(n+1): the rail roots are v3 and v6
    s.add("sketch.fillet", points=["l2.end", "l5.end"], radius="root_r")
    s.add("sketch.finish")
    s.add("solid.extrude", distance="plate_h", direction="symmetric", operation="new", body_name="Mount", name="Mount")

    s.step("Screw holes")
    for sx in ("", "0 mm - "):
        s.add("solid.hole", position=[f"{sx}hole_dx", "0 mm", "0 mm"], diameter="hole_d", type="countersink", cs_diameter="cs_d",
              cs_angle="90 deg", targets=["Mount"])

    s.step("Corners")
    px, py, pz = V["plate_w"] / 2, V["plate_h"] / 2, -V["plate_t"] / 2
    s.add("solid.fillet", body="Mount", radius="plate_r", edges=[[sx * px, sy * py, pz] for sx in (1, -1) for sy in (1, -1)], name="Mount_corners")

    s.add("appearance.assign", bodies=["Plaque", "Mount"], color="#1d1f22")
    s.add("appearance.assign", bodies=["Number"], color="#f2f2f2")
    return s.steps


def number_commands(key):
    """The raised digits on the plaque's front as body "Number", centred by text_dx/text_dy."""
    return [
        {"command": "sketch.create", "params": {"plane": "XY", "offset": "plaque_t"}},
        {"command": "sketch.text", "params": {"text": str(key), "at": ["text_dx", "text_dy - text_h / 2"], "height": "text_h",
                                              "font": FONT, "bold": True, "align": "center"}},
        {"command": "sketch.finish", "params": {}},
        {"command": "solid.extrude", "params": {"distance": "text_t", "operation": "new", "body_name": "Number", "profiles": "all", "name": "Number"}},
    ] + ([] if pieces(key) < 2 else [
        {"command": "solid.combine", "params": {"target": "Number", "tools": [f"Number ({k})" for k in range(2, pieces(key) + 1)], "operation": "join"}}])


def pieces(key):
    """Separate pieces the digits come out as: one per digit, and the dot inside this font's zero."""
    return len(str(key)) + str(key).count("0")


def text_script(key, text=None):
    """Just the parameters and the digits, to measure their outline quickly."""
    st = steps(key, text)
    return {"commands": st[0][1] + number_commands(key)}


def script(key, text=None):
    return {"commands": [c for _, cs in steps(key, text) for c in cs]}


def defects(result):
    """Problems in a `solidcraft-cli eval` result: timeline errors and warnings, rolled-back steps,
    booleans the kernel had to nudge or truncated, and bodies other than the three.
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
    if bodies != ["Mount", "Number", "Plaque"]:
        out.append(f"bodies {bodies}, expected Mount, Number and Plaque")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    json.dump(script(int(sys.argv[2])), open(sys.argv[1], "w"), indent=1)
