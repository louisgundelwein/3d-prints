"""Generates the SolidCraft script for a 3U 19" rack mount holding four Mac mini (M4) in two
stacks of two, standing upright on their feet.

Usage: python -I build.py OUT.json [--macs MAC.step]

--macs places four Mac minis from that STEP file (127 x 127 x 50.8 mm, origin at the front left
bottom corner, front towards -Y) in the bays, to check the fit. The repository leaves them out:
the Mac model is third-party.

Every length in the model is a user parameter or an expression of user parameters.

Coordinates: X across the rack (0 = left panel edge), Y into the rack (0 = panel front),
Z up (0 = panel bottom edge).

The rack is two halves split at X = mid. Each half is one extrusion of its XZ profile along Y
(walls, plates, gussets in one sketch) plus the faceplate, so it prints standing on its front
face without supports. The halves slide together on dovetails; the rack rails fix them in Y.
"""
import json
import math
import os
import re
import sys


# name -> (expression, comment)
P = {
    # rack
    "U": ("44.45 mm", "EIA-310 rack unit"),
    "panel_gap": ("0.79 mm", "EIA-310 clearance between stacked panels"),
    "panel_h": ("3 * U - panel_gap", "3U panel height"),
    "panel_w": ("482.6 mm", "19 inch panel incl. ears"),
    "mid": ("panel_w / 2", "split line between the two printed halves"),
    "rail_pitch": ("465 mm", "rail hole spacing across the rack"),
    "rack_open": ("450 mm", "smallest clear width between the rails"),
    "rail_gap": ("3 mm", "clearance between body and rail (room for the ear's root fillet)"),
    "side_x": ("(panel_w - rack_open) / 2 + rail_gap", "outer face of the body side walls"),
    "hole_x": ("(panel_w - rail_pitch) / 2", "ear hole centre from the panel edge"),
    "hole_e": ("6.35 mm", "EIA-310 hole centre above a unit's bottom"),
    "m6_d": ("7 mm", "M6 clearance"),
    "m6_slot": ("4 mm", "horizontal slot length of the ear holes"),
    # Mac mini M4, measured from reference/mac_mini_m4.step
    "mac_w": ("127 mm", "Mac mini width and depth"),
    "mac_h": ("50.8 mm", "Mac mini height incl. foot"),
    "mac_r": ("25.4 mm", "Mac mini corner radius (plan view)"),
    "foot_h": ("6.35 mm", "height of the housing's bottom edge above the foot's contact face"),
    # body
    "face_t": ("6 mm", "faceplate thickness"),
    "wall_t": ("5 mm", "outer side wall"),
    "plate_t": ("5 mm", "bottom, middle and top plate"),
    "spine_t": ("16 mm", "centre wall of each half, carries the dovetails"),
    "gus": ("6 mm", "fillet radius in the inside corners of the bays' ceilings"),
    "gus_floor": ("3 mm", "fillet radius where a Mac's edge passes (bay floor)"),
    "fit": ("1 mm", "side clearance around a Mac"),
    "mac_y": ("1 mm", "Mac front behind the panel front"),
    "bay_w": ("mac_w + 2 * fit", "clear width of a bay"),
    "bay_h": ("(panel_h - 3 * plate_t) / 2", "clear height of a bay"),
    "bay_wall_t": ("5 mm", "wall between a bay and the free space next to it"),
    "gus_c": ("15 mm", "fillet radius in the free space next to the bays (braces the middle plate)"),
    "edge_r": ("3 mm", "outer edges of the body along its depth"),
    "ear_r": ("5 mm", "faceplate corners"),
    "ear_root_r": ("min(rail_gap - 1 mm, edge_r - 0.5 mm)", "fillet where the ear meets the outer wall (the ear carries the rack, across print layers)"),
    "ws_r": ("4 mm", "side corners of the cable slots"),
    "ws_h": ("24 mm", "height of the cable slots in the bay walls"),
    "ws_e": ("20 mm", "cable slots' distance from the front and back"),
    "ws_web": ("10 mm", "web between the two cable slots of a bay wall"),
    "stop_h": ("12 mm", "rear stop height; its 45 degree face meets the housing edge at foot_h"),
    "stop_w": ("25 mm", "rear stop width"),
    "stop_back": ("1 mm", "rear stop ends this far in front of the back face"),
    "stop_r": ("3 mm", "rounded top of the rear stop"),
    "stop_foot_r": ("4 mm", "fillet between the rear stop and the floor"),
    "depth": ("mac_y + mac_w - foot_h + stop_h", "body depth: the stop's slope reaches the back"),
    "btn_w": ("20 mm", "power button slot width (rear left of each Mac, open to the back)"),
    "btn_x": ("18 mm", "power button slot centre from the Mac's left side (estimate)"),
    "btn_l": ("30 mm", "power button slot reaches this far in front of the Mac's back"),
    # dovetails between the halves
    "dt_root": ("16 mm", "dovetail width at the split line"),
    "dt_tip": ("24 mm", "dovetail width at its tip"),
    "dt_d": ("10 mm", "dovetail depth"),
    "dt_c": ("0.25 mm", "dovetail clearance per side, square to every face"),
    "dt_s": ("(dt_tip - dt_root) / (2 * dt_d)", "dovetail flank slope"),
    "dt_cv": ("dt_c * sqrt(1 + dt_s * dt_s)", "vertical shift of a flank that moves it dt_c square to itself"),
    "dt_e": ("22 mm", "outer dovetails' centre from the top and bottom"),
    # latches
    "latch_t": ("4 mm", "latch thickness"),
    "latch_w": ("12 mm", "latch width"),
    "latch_z": ("38 mm", "latch centre above the floor (clear of the headphone jack)"),
    "boss_gap": ("1 mm", "room between the screw boss's foot fillet and the bay wall"),
    "latch_over": ("6 mm", "how far the latch reaches over the flat part of the Mac's front"),
    "latch_hole": ("4.4 mm", "M4 clearance in the latch"),
    "screw_core": ("3.4 mm", "hole the M4 screw cuts its own thread in"),
    "boss_d": ("10 mm", "screw boss behind the faceplate"),
    "boss_l": ("12 mm", "screw boss length"),
    "boss_r": ("3 mm", "fillet where the screw boss meets the faceplate"),
    "latch_px": ("boss_d / 2 + boss_r + boss_gap", "latch pivot beside the bay wall"),
    "boss_end_r": ("1 mm", "rounded end of the screw boss"),
    "latch_r": ("1.5 mm", "rounded front edges of the latch"),
    # cable management
    "fin_e": ("5 mm", "cable hole behind the body"),
    "big_w": ("22 mm", "cable hole height"),
    "big_l": ("32 mm", "cable hole length (meant for HDMI, power and LAN plugs; plug sizes not measured)"),
    "fin_back": ("8 mm", "wall left behind the cable hole"),
    "fin_l": ("fin_e + big_l + fin_back", "the bay wall reaches this far behind the body, for cable routing"),
    "fin_r": ("10 mm", "rounded rear corners of the bay wall's extension"),
    "notch_h": ("10 mm", "cable notches through the spines, open to the back"),
    "notch_web": ("3 mm", "material left between a cable notch and the dovetail slot"),
    "notch_l": ("40 mm", "cable notch length from the back"),
    "eps": ("0.5 mm", "overlap of joins and overshoot of cuts"),
}

XZ = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (X, Z), normal -Y
YZ = {"origin": [0, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (Y, Z), normal +X
XY = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, 1, 0]}   # (x, y) = world (X, Y), normal +Z

def ev(expr):
    """Numeric value in mm of a length expression over the parameters (edge picks only)."""
    return eval(re.sub(r"\bmm\b", "", expr), {"__builtins__": {}, "sqrt": math.sqrt, "min": min}, V)


V = {}
for _k, (_e, _c) in P.items():
    V[_k] = ev(_e)

L, R = "Rack_links", "Rack_rechts"
cmds = []


def add(command, **params):
    cmds.append({"command": command, "params": params})


def box(body, corner, size, op="join", name=None):
    """Box joined to or cut from body."""
    p = {"length": size[0], "width": size[1], "height": size[2], "corner": list(corner), "operation": op, "targets": [body]}
    if name:
        p["name"] = name
    add("solid.box", **p)


BAY_X0 = "side_x + wall_t"                              # left half: bay between these two
BAY_X1 = "side_x + wall_t + bay_w"
FREE_X0 = "side_x + wall_t + bay_w + bay_wall_t"         # free space between these two
FREE_X1 = "mid - spine_t"


def rect(x0, x1, z0, z1):
    """Rectangle as a closed polygon; its lines run bottom, right, top, left, so line k's end is
    the corner bottom-right, top-right, top-left, bottom-left."""
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


FLOORS = ["plate_t", "2 * plate_t + bay_h"]           # top face of the plate each Mac stands on


def drop(y0, y1, zc, w):
    """Oval hole along Y in a YZ sketch: a half circle at the front, pointed at 45 degrees at the
    back (up when printing), the shoulders rounded. Adds 4 lines and an arc."""
    yr = f"{y0} + {w} / 2"
    add("sketch.line", points=[[yr, f"{zc} - {w} / 2"], [f"{y1} - {w} / 2", f"{zc} - {w} / 2"], [y1, zc],
                               [f"{y1} - {w} / 2", f"{zc} + {w} / 2"], [yr, f"{zc} + {w} / 2"]], infer=False)
    add("sketch.arc.center_point", center=[yr, zc], start=[yr, f"{zc} + {w} / 2"], end=[yr, f"{zc} - {w} / 2"])


class Side:
    """One half. Geometry is written for the left half (X from the rail side towards mid); the
    right half maps every X across mid, which also reverses the turning sense of arcs."""

    def __init__(self, body, right, latches):
        self.body, self.right, self.latches = body, right, latches

    def x(self, e):
        return f"panel_w - ({e})" if self.right else e

    def span(self, x0, w):
        """Start of an X range [x0, x0 + w] after mapping; its width stays w."""
        return f"panel_w - ({x0}) - ({w})" if self.right else x0

    def num(self, x):
        return ev("panel_w") - x if self.right else x

    def pts(self, poly):
        return [[self.x(px), pz] for px, pz in poly]

    def arc(self, center, start, end):
        """Arc running counter-clockwise from start to end on the left half."""
        c, a, b = self.pts([center, start, end])
        if self.right:
            a, b = b, a
        add("sketch.arc.center_point", center=c, start=a, end=b)


def mid_edge(side):
    """The split edge of the profile, bottom to top, in left-half coordinates: the left half
    carries the dovetail tabs, the right half the slots (the tab offset by dt_c square to every
    face), both running the full depth."""
    pts = []
    for z in ["dt_e", "panel_h / 2", "panel_h - dt_e"]:
        if side.right:
            d = "(dt_d + dt_c)"
            pts += [("mid", f"{z} - dt_root / 2 - dt_cv"), (f"mid - {d}", f"{z} - dt_root / 2 - dt_s * {d} - dt_cv"),
                    (f"mid - {d}", f"{z} + dt_root / 2 + dt_s * {d} + dt_cv"), ("mid", f"{z} + dt_root / 2 + dt_cv")]
        else:
            pts += [("mid", f"{z} - dt_root / 2"), ("mid + dt_d", f"{z} - dt_tip / 2"),
                    ("mid + dt_d", f"{z} + dt_tip / 2"), ("mid", f"{z} + dt_root / 2")]
    return pts


def profile(side):
    """Walls, plates, centre wall, dovetail and all their inside roundings: one sketch, one
    extrusion over the body's depth."""
    levels = [(FLOORS[0], "plate_t + bay_h"), (FLOORS[1], "panel_h - plate_t")]
    outer = [("side_x", "0 mm"), ("mid", "0 mm")] + mid_edge(side) + [("mid", "panel_h"), ("side_x", "panel_h")]
    cells = [rect(BAY_X0, FREE_X1, z0, z1) for z0, z1 in levels]     # the bay wall comes from bay_wall()
    add("sketch.create", plane=XZ)
    for poly in [outer] + cells:
        add("sketch.line", points=side.pts(poly), closed=True, infer=False)
    n = len(outer)
    c = lambda k, i: f"l{n + 4 * k + i}.end"     # cell k's corners: bottom-right, top-right, top-left, bottom-left
    add("sketch.fillet", points=[f"l{n - 1}.end", f"l{n}.end"], radius="edge_r")       # outer, rail side
    add("sketch.fillet", points=[c(0, 4), c(1, 4)], radius="gus_floor")                 # bay floors at the outer wall
    add("sketch.fillet", points=[c(0, 3), c(1, 3)], radius="gus")                       # bay ceilings at the outer wall
    add("sketch.fillet", points=[c(k, i) for k in (0, 1) for i in (1, 2)], radius="gus_c")  # at the centre wall
    add("sketch.finish")
    wall = [side.num(ev("side_x + wall_t / 2")), ev("panel_h / 2")]
    add("solid.extrude", distance="depth", direction="negative", operation="new", body_name=side.body, name="Profil",
        profiles=[{"point": wall}])


def faceplate(side):
    """The ear strip (ending inside the outer wall, past its edge rounding) and a cover over the
    free space next to the bay."""
    add("sketch.create", plane=XZ)
    add("sketch.line", points=side.pts(rect("0 mm", "side_x + (edge_r + wall_t) / 2", "0 mm", "panel_h")), closed=True, infer=False)
    add("sketch.fillet", points=["l3.end", "l4.end"], radius="ear_r")
    add("sketch.finish")
    add("solid.extrude", distance="face_t", direction="negative", operation="join", targets=[side.body], name="Frontplatte_Ohr")
    # ends inside the centre wall, clear of the dovetail slot of the right half
    x0, w = f"{BAY_X1} + bay_wall_t / 2", f"mid - (spine_t + dt_d + dt_c) / 2 - ({BAY_X1} + bay_wall_t / 2)"
    box(side.body, [side.span(x0, w), "0 mm", "plate_t / 2"], [w, "face_t", "panel_h - plate_t"], name="Frontplatte_Mitte")


def bay_wall(side):
    """The wall between bay and free space, from the faceplate to fin_l behind the body: one plan
    sketch extruded between the mid-planes of the bottom and top plate, so its faces run through
    without a step (Y is up when printing). Its fillets to the plates and its rounded rear corners
    come last (fillets())."""
    add("sketch.create", plane="XY", offset="plate_t / 2")
    add("sketch.line", points=side.pts(rect(BAY_X1, FREE_X0, "0 mm", "depth + fin_l")), closed=True, infer=False)
    add("sketch.finish")
    add("solid.extrude", distance="panel_h - plate_t", operation="join", targets=[side.body],
        profiles=[{"point": [side.num(ev(f"{BAY_X1} + bay_wall_t / 2")), ev("depth / 2")]}], name="Fachwand")


def bosses(side):
    """Screw bosses for the latches, revolved, starting inside the faceplate, their ends rounded
    in the sketch (foot fillets come last); and the latches themselves (separate bodies, drawn
    locked: over the flat part of the Mac's front; turned by 180 degrees they lie over the faceplate)."""
    px = f"{FREE_X0} + latch_px"
    reach = "side_x + wall_t + fit + mac_w - mac_r - latch_over"
    for zf, name in zip(FLOORS, side.latches):
        pz = f"{zf} + latch_z"
        add("sketch.create", plane="XY", offset=pz)
        add("sketch.line", points=side.pts([(px, "face_t / 2"), (f"{px} + boss_d / 2", "face_t / 2"),
                                            (f"{px} + boss_d / 2", "face_t + boss_l"), (px, "face_t + boss_l")]), closed=True, infer=False)
        add("sketch.fillet", points=["l2.end"], radius="boss_end_r")
        add("sketch.finish")
        add("solid.revolve", axis="l4", operation="join", targets=[side.body], name="Dom")
        w = f"{px} - ({reach})"
        add("solid.box", length=w, width="latch_t", height="latch_w",
            corner=[side.span(reach, w), "0 mm - latch_t", f"{pz} - latch_w / 2"], body_name=name)
        for x in (reach, px):
            add("solid.cylinder", diameter="latch_w", height="latch_t", axis="Y", base=[side.x(x), "0 mm - latch_t", pz],
                operation="join", targets=[name])
        add("solid.cylinder", diameter="latch_hole", height="latch_t + 2 * eps", axis="Y",
            base=[side.x(px), "0 mm - latch_t - eps", pz], operation="cut", targets=[name])


def stops(side, xl):
    """Rear stop of each bay, right of the Mac seen from the front; xl = the bay's left wall (not
    mapped: the stop and the power button sit on the same side of every Mac). The 45 degree slope
    starts foot_h in front of the Mac's back, so it meets the housing's bottom edge, never the foot;
    it runs on into the plate, so the stop starts inside material (foot fillet comes last)."""
    y_s, y_e = "mac_y + mac_w - foot_h", "depth - stop_back"
    for zf in FLOORS:
        add("sketch.create", plane=YZ)
        add("sketch.line", points=[[f"{y_s} - plate_t / 2", f"{zf} - plate_t / 2"], [y_e, f"{zf} - plate_t / 2"],
                                   [y_e, f"{zf} + stop_h - stop_back"]], closed=True, infer=False)
        add("sketch.fillet", points=["l2.end"], radius="stop_r")
        add("sketch.finish")
        add("solid.extrude", distance="stop_w", start_offset=f"{xl} + fit + mac_w - mac_r - stop_w",
            operation="join", targets=[side.body], name="Anschlag")


def cuts(side, xl):
    """Every hole and slot of a half, after all its joins."""
    body = side.body
    # M6 slots for the rails: bottom unit, middle unit, top unit
    for k, z in enumerate(["hole_e - panel_gap / 2", "1.5 * U - panel_gap / 2", "3 * U - hole_e - panel_gap / 2"]):
        box(body, [side.span("hole_x - m6_slot / 2", "m6_slot"), "0 mm - eps", f"{z} - m6_d / 2"], ["m6_slot", "face_t + 2 * eps", "m6_d"],
            op="cut", name=f"Ohr{k}")
        for sx in ("-", "+"):
            add("solid.cylinder", diameter="m6_d", height="face_t + 2 * eps", axis="Y",
                base=[side.x(f"hole_x {sx} m6_slot / 2"), "0 mm - eps", z], operation="cut", targets=[body])
    # cable and air slots in the bay wall, pointed at 45 degrees towards front and back
    for zf in FLOORS:
        zc = f"{zf} + bay_h / 2"
        add("sketch.create", plane=YZ)
        for y0, y1 in (("ws_e", "depth / 2 - ws_web / 2"), ("depth / 2 + ws_web / 2", "depth - ws_e")):
            add("sketch.line", points=[[y0, zc], [f"{y0} + ws_h / 2", f"{zc} - ws_h / 2"], [f"{y1} - ws_h / 2", f"{zc} - ws_h / 2"],
                                       [y1, zc], [f"{y1} - ws_h / 2", f"{zc} + ws_h / 2"], [f"{y0} + ws_h / 2", f"{zc} + ws_h / 2"]],
                closed=True, infer=False)
        add("sketch.fillet", points=[f"l{6 * k + i}.end" for k in (0, 1) for i in (1, 2, 4, 5)], radius="ws_r")
        add("sketch.finish")
        add("solid.extrude", distance="bay_wall_t + 2 * eps", start_offset=side.span(f"{BAY_X1} - eps", "bay_wall_t + 2 * eps"),
            operation="cut", targets=[body], profiles="all", name="Fachwand_Schlitze")
    # cable hole per level through the bay wall's extension: a half circle at the front, a
    # 45 degree point at the back
    add("sketch.create", plane=YZ)
    for k, zf in enumerate(FLOORS):
        drop("depth + fin_e", "depth + fin_e + big_l", f"{zf} + bay_h / 2", "big_w")
        add("sketch.fillet", points=[f"l{4 * k + 1}.end", f"l{4 * k + 3}.end"], radius="big_w / 4")
    add("sketch.finish")
    w = "bay_wall_t + 2 * eps"
    add("solid.extrude", distance=w, start_offset=side.span(f"{BAY_X1} - eps", w), operation="cut",
        targets=[body], profiles="all", name="Kabelloecher")
    # cable notches through the centre wall, open to the back, with half-round ends; centred
    # between the outer dovetails and the fillets of the free space
    zc = "dt_e + dt_root / 2 + dt_s * (dt_d + dt_c) + dt_cv + notch_web + notch_h / 2"
    yr = "depth - notch_l + notch_h / 2"
    add("sketch.create", plane=YZ)
    for z in (zc, f"panel_h - ({zc})"):
        add("sketch.line", points=[[yr, f"{z} - notch_h / 2"], ["depth + eps", f"{z} - notch_h / 2"], ["depth + eps", f"{z} + notch_h / 2"],
                                   [yr, f"{z} + notch_h / 2"]], infer=False)
        add("sketch.arc.center_point", center=[yr, z], start=[yr, f"{z} + notch_h / 2"], end=[yr, f"{z} - notch_h / 2"])
    add("sketch.finish")
    w = "spine_t + dt_d + dt_c + 2 * eps"
    add("solid.extrude", distance=w, start_offset=side.span("mid - spine_t - eps", w), operation="cut", targets=[body],
        profiles="all", name="Kabelschlitze")
    # screw holes in the bosses
    for zf in FLOORS:
        add("solid.cylinder", diameter="screw_core", height="face_t + boss_l", axis="Y",
            base=[side.x(f"{FREE_X0} + latch_px"), "0 mm - eps", f"{zf} + latch_z"], operation="cut", targets=[body])
    # power button: slot with a round end under the Mac's rear left corner, open to the back,
    # clear of the wall and its fillets (not mapped, like the stops)
    for zf in FLOORS:
        cx = f"{xl} + fit + btn_x"
        yc = "mac_y + mac_w - btn_l + btn_w / 2"
        add("sketch.create", plane="XY", offset=f"{zf} - plate_t - eps")
        add("sketch.line", points=[[f"{cx} + btn_w / 2", yc], [f"{cx} + btn_w / 2", "depth + eps"],
                                   [f"{cx} - btn_w / 2", "depth + eps"], [f"{cx} - btn_w / 2", yc]], infer=False)
        add("sketch.arc.center_point", center=[cx, yc], start=[f"{cx} - btn_w / 2", yc], end=[f"{cx} + btn_w / 2", yc])
        add("sketch.finish")
        add("solid.extrude", distance="plate_t + 2 * eps", operation="cut", targets=[body], profiles="all", name="Knopf")


def fillet(body, radius, points, name):
    add("solid.fillet", body=body, radius=radius, edges=[[round(v, 4) for v in pt] for pt in points], name=name)


def fillets():
    """Last in the timeline, after every join and cut: the roundings no sketch can carry. Edges
    are picked at the default parameter values and mirrored about mid for the right half."""
    mx = lambda x, side: x if side == L else ev("panel_w") - x
    zs = [ev(f"{zf} + latch_z") for zf in FLOORS]
    px = ev(f"{FREE_X0} + latch_px")
    y_s = ev("mac_y + mac_w - foot_h")
    wall_c = ev(f"{BAY_X1} + bay_wall_t / 2")
    wall_corners = [[wall_c, ev("depth + fin_l"), z] for z in (ev("plate_t / 2"), ev("panel_h - plate_t / 2"))]
    floors = [ev(z) for z in FLOORS]
    ceilings = [ev("plate_t + bay_h"), ev("panel_h - plate_t")]
    ym = ev("depth / 2")
    for side, xl in ((L, ev("side_x + wall_t")), (R, ev("panel_w - side_x - wall_t - bay_w"))):
        tag = "L" if side == L else "R"
        fillet(side, "boss_r", [[mx(px, side), ev("face_t"), z + ev("boss_d / 2")] for z in zs], f"Dom_Fuss_{tag}")
        bay_x, free_x = mx(ev(BAY_X1), side), mx(ev(FREE_X0), side)
        fillet(side, "gus_floor", [[bay_x, ym, z] for z in floors], f"Fachwand_Boden_{tag}")
        fillet(side, "gus", [[bay_x, ym, z] for z in ceilings], f"Fachwand_Decke_{tag}")
        fillet(side, "gus_c", [[free_x, ym, z] for z in floors + ceilings], f"Fachwand_Mitte_{tag}")
        fillet(side, "fin_r", [[mx(x, side), y, z] for x, y, z in wall_corners], f"Fachwand_Ecken_{tag}")
        fillet(side, "ear_root_r", [[mx(ev("side_x"), side), ev("face_t"), ev("panel_h / 2")]], f"Ohr_Uebergang_{tag}")
        x_stop = xl + ev("fit + mac_w - mac_r - stop_w / 2")
        fillet(side, "stop_foot_r", [[x_stop, y_s, ev(zf)] for zf in FLOORS], f"Anschlag_Fuss_{tag}")
    for k, name in enumerate(["Riegel_1", "Riegel_2", "Riegel_3", "Riegel_4"]):
        side = L if k < 2 else R
        z = zs[k % 2]
        reach = ev("side_x + wall_t + fit + mac_w - mac_r - latch_over")
        y = -ev("latch_t")
        fillet(name, "latch_r", [[mx((reach + px) / 2, side), y, z - ev("latch_w / 2")], [mx((reach + px) / 2, side), y, z + ev("latch_w / 2")],
                                 [mx(reach - ev("latch_w / 2"), side), y, z], [mx(px + ev("latch_w / 2"), side), y, z]], f"Riegel_Kante_{k + 1}")


def macs(step):
    """The four Macs from the reference model, placed by parameter expressions."""
    add("file.insert_step", path=os.path.abspath(step), name="Mac")
    xls = ["side_x + wall_t", "panel_w - side_x - wall_t - bay_w"]
    spots = [(x, z) for x in xls for z in FLOORS]
    for x, z in spots[1:]:
        add("solid.move", bodies=["root"], translate=[f"{x} + fit", "mac_y", z], copy=True)
    add("solid.move", bodies=["root"], translate=[f"{spots[0][0]} + fit", "mac_y", spots[0][1]])
    # the copies first: renaming "root" first renames its copies with it
    for k, name in [(2, "root (2)"), (3, "root (3)"), (4, "root (4)"), (1, "root")]:
        add("body.rename", body=name, name=f"Mac_{k}")


def build(mac_step=None):
    for k, (e, c) in P.items():
        add("parameters.add", name=k, expression=e, comment=c)
    halves = [(Side(L, False, ["Riegel_1", "Riegel_2"]), "side_x + wall_t"),
              (Side(R, True, ["Riegel_3", "Riegel_4"]), "panel_w - side_x - wall_t - bay_w")]
    for side, xl in halves:
        profile(side)
        faceplate(side)
        bay_wall(side)
        bosses(side)
        stops(side, xl)
        cuts(side, xl)
    fillets()
    if mac_step:
        macs(mac_step)
    return {"commands": cmds}


if __name__ == "__main__":
    args = sys.argv[1:]
    step = None
    if "--macs" in args:
        i = args.index("--macs")
        step = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        raise SystemExit(__doc__)
    json.dump(build(step), open(args[0], "w"), indent=1)
