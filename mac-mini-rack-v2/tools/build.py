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
    "fin_lip": ("1.5 mm", "the rib's foot is this much wider than its wall on each side, joined to the wall at 45 degrees"),
    "rail_gap": ("fin_lip + 1 mm", "clearance between body and rail; the outer rib feet stick out fin_lip"),
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
    "ear_root_r": ("edge_r - 0.5 mm", "fillet where the ear meets the outer wall (the ear carries the rack, across print layers)"),
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
    "dt_cap": ("5 mm", "solid end of the right half's slots: stop for sliding the halves together"),
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
    "fin_back": ("10 mm", "wall left behind the last cable hole"),
    "fin_t": ("3 mm", "cable rib thickness, centred on its wall"),
    "fin_inset": ("edge_r + 1 mm", "cable ribs stay this far inside the top and bottom faces, clear of the edge roundings"),
    "fin_r": ("10 mm", "rounded rear corners of the cable ribs"),
    "fin_flare": ("6 mm", "the rib narrows from its foot to fin_t along concave arcs over this length"),
    "fin_e": ("fin_lip + fin_flare + 4 mm", "first cable hole behind the body"),
    "big_w": ("22 mm", "large cable hole: height"),
    "big_l": ("32 mm", "large cable hole: length (meant for HDMI, power and LAN plugs; plug sizes not measured)"),
    "small_w": ("10 mm", "small cable hole: height"),
    "small_l": ("16 mm", "small cable hole: length"),
    "hole_gap": ("6 mm", "web between the large and the small cable hole"),
    "fin_l": ("fin_e + big_l + hole_gap + small_l + fin_back", "cable ribs reach this far behind the body"),
    "notch_h": ("12 mm", "cable notches through the spines, open to the back"),
    "notch_l": ("40 mm", "cable notch length from the back"),
    "eps": ("0.5 mm", "overlap of joins and overshoot of cuts"),
}

XZ = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (X, Z), normal -Y
YZ = {"origin": [0, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}   # (x, y) = world (Y, Z), normal +X
XY = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, 1, 0]}   # (x, y) = world (X, Y), normal +Z

def ev(expr):
    """Numeric value in mm of a length expression over the parameters (edge picks only)."""
    return eval(re.sub(r"\bmm\b", "", expr), {"__builtins__": {}, "sqrt": math.sqrt}, V)


V = {}
for _k, (_e, _c) in P.items():
    V[_k] = ev(_e)

L, R = "Rack_links", "Rack_rechts"
cmds = []


def add(command, **params):
    cmds.append({"command": command, "params": params})


def sketch(plane, polys):
    """Sketch of closed polygons with parametric vertices [[x_expr, y_expr], ...]."""
    add("sketch.create", plane=plane)
    for poly in polys:
        add("sketch.line", points=[list(p) for p in poly], closed=True, infer=False)
    add("sketch.finish")


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


def half():
    """Left half: profile extrusion, faceplate, rail ear slots."""
    levels = [(FLOORS[0], "plate_t + bay_h"), (FLOORS[1], "panel_h - plate_t")]
    add("sketch.create", plane=XZ)
    polys = [rect("side_x", "mid", "0 mm", "panel_h")]
    polys += [rect(BAY_X0, BAY_X1, z0, z1) for z0, z1 in levels]
    polys += [rect(FREE_X0, FREE_X1, z0, z1) for z0, z1 in levels]
    for poly in polys:
        add("sketch.line", points=[list(p) for p in poly], closed=True, infer=False)
    # corners: line 4k+1 .. 4k+4 belong to polygon k; .end of bottom, right, top, left line
    c = lambda k, i: f"l{4 * k + i}.end"
    add("sketch.fillet", points=[c(0, 3), c(0, 4)], radius="edge_r")                 # outer, rail side
    add("sketch.fillet", points=[c(1, 1), c(1, 4), c(2, 1), c(2, 4)], radius="gus_floor")  # bay floors
    add("sketch.fillet", points=[c(1, 2), c(1, 3), c(2, 2), c(2, 3)], radius="gus")        # bay ceilings
    add("sketch.fillet", points=[c(k, i) for k in (3, 4) for i in (1, 2, 3, 4)], radius="gus_c")
    add("sketch.finish")
    wall = [ev("side_x + wall_t / 2"), ev("panel_h / 2")]
    add("solid.extrude", distance="depth", direction="negative", operation="new", body_name=L, name="Profil",
        profiles=[{"point": wall}])
    # faceplate: the ear strip, and a cover over the free space next to the bays
    add("sketch.create", plane=XZ)
    add("sketch.line", points=[list(p) for p in rect("0 mm", "side_x + (edge_r + wall_t) / 2", "0 mm", "panel_h")], closed=True, infer=False)
    add("sketch.fillet", points=["l3.end", "l4.end"], radius="ear_r")
    add("sketch.finish")
    add("solid.extrude", distance="face_t", direction="negative", operation="join", targets=[L], name="Frontplatte_Ohr")
    box(L, [f"{BAY_X1} + bay_wall_t / 2", "0 mm", "plate_t / 2"],
        [f"mid - spine_t / 2 - ({BAY_X1} + bay_wall_t / 2)", "face_t", "panel_h - plate_t"], name="Frontplatte_Mitte")
    # M6 slots for the rails: bottom unit, middle unit, top unit
    for k, z in enumerate(["hole_e - panel_gap / 2", "1.5 * U - panel_gap / 2", "3 * U - hole_e - panel_gap / 2"]):
        box(L, ["hole_x - m6_slot / 2", "0 mm - eps", f"{z} - m6_d / 2"], ["m6_slot", "face_t + 2 * eps", "m6_d"],
            op="cut", name=f"Ohr{k}")
        for sx in ("-", "+"):
            add("solid.cylinder", diameter="m6_d", height="face_t + 2 * eps", axis="Y",
                base=[f"hole_x {sx} m6_slot / 2", "0 mm - eps", z], operation="cut", targets=[L])


def bay_wall_slots():
    """Two slots per level through the left half's bay wall, pointed at 45 degrees towards front
    and back so they print without support (Y is up when printing)."""
    for zf in FLOORS:
        zc = f"{zf} + bay_h / 2"
        polys = []
        for y0, y1 in (("ws_e", "depth / 2 - ws_web / 2"), ("depth / 2 + ws_web / 2", "depth - ws_e")):
            polys.append([(y0, zc), (f"{y0} + ws_h / 2", f"{zc} - ws_h / 2"), (f"{y1} - ws_h / 2", f"{zc} - ws_h / 2"),
                          (y1, zc), (f"{y1} - ws_h / 2", f"{zc} + ws_h / 2"), (f"{y0} + ws_h / 2", f"{zc} + ws_h / 2")])
        add("sketch.create", plane=YZ)
        for poly in polys:
            add("sketch.line", points=[list(p) for p in poly], closed=True, infer=False)
        add("sketch.fillet", points=[f"l{6 * k + i}.end" for k in (0, 1) for i in (1, 2, 4, 5)], radius="ws_r")
        add("sketch.finish")
        add("solid.extrude", distance="bay_wall_t + 2 * eps", start_offset=f"{BAY_X1} - eps", operation="cut",
            targets=[L], profiles="all")


def drop(y0, y1, zc, w):
    """Oval hole along Y, rounded at the front, pointed at 45 degrees at the back (up when printing)."""
    return [(y0, f"{zc} - {w} / 2"), (f"{y1} - {w} / 2", f"{zc} - {w} / 2"), (y1, zc),
            (f"{y1} - {w} / 2", f"{zc} + {w} / 2"), (y0, f"{zc} + {w} / 2")]


def rib(centre, wall, name):
    """Cable rib behind a wall, as a plan outline (XY sketch) extruded over the rib's height. Its
    foot sits on the wall's last stretch, fin_lip wider than the wall on each side and joined to
    it at 45 degrees; from there it narrows to fin_t along concave arcs over fin_flare. So the
    section changes over many print layers instead of stepping at one (Y is up when printing),
    and none of its faces lies in a plane of the wall."""
    xa, xb = f"{centre} - {wall} / 2 - fin_lip", f"{centre} + {wall} / 2 + fin_lip"   # foot faces
    wa, wb = f"{centre} - {wall} / 2", f"{centre} + {wall} / 2"                       # wall faces
    ra, rb = f"{centre} - fin_t / 2", f"{centre} + fin_t / 2"                         # rib faces
    step = f"({wall} / 2 + fin_lip - fin_t / 2)"
    arc_r = f"({step} * {step} + fin_flare * fin_flare) / (2 * {step})"                # through the foot corner
    # the foot reaches fin_lip into and fin_lip out of the body, so no rib edge lies in the back face
    y0, yf, y1, y2 = "depth - fin_lip", "depth + fin_lip", "depth + fin_lip + fin_flare", "depth + fin_l"
    add("sketch.create", plane="XY", offset="fin_inset")
    # the 45 degree faces run on eps into the wall, so the foot's corners lie inside it, not on its faces
    add("sketch.line", points=[[xb, yf], [xb, y0], [f"{wb} - eps", f"{y0} - fin_lip - eps"], [f"{wa} + eps", f"{y0} - fin_lip - eps"],
                               [xa, y0], [xa, yf]], infer=False)
    add("sketch.arc.center_point", center=[f"{ra} - {arc_r}", y1], start=[xa, yf], end=[ra, y1])
    add("sketch.line", points=[[ra, y1], [ra, y2], [rb, y2], [rb, y1]], infer=False)
    add("sketch.arc.center_point", center=[f"{rb} + {arc_r}", y1], start=[rb, y1], end=[xb, yf])
    add("sketch.finish")
    add("solid.extrude", distance="panel_h - 2 * fin_inset", operation="join", targets=[L],
        profiles=[{"point": [ev(centre), ev("depth + fin_l / 2")]}], name=name)


def fins():
    """Left half: a cable rib behind the outer wall and one behind the bay wall, then a large and
    a small cable hole per level through both (pointed at 45 degrees towards the back, up when
    printing)."""
    rib("side_x + wall_t / 2", "wall_t", "Kabelrippe_aussen")
    rib(f"{BAY_X1} + bay_wall_t / 2", "bay_wall_t", "Kabelrippe_Fach")
    y_big, y_small = "depth + fin_e", "depth + fin_e + big_l + hole_gap"
    add("sketch.create", plane=YZ)
    polys = []
    for zf in FLOORS:
        zc = f"{zf} + bay_h / 2"
        polys += [drop(y_big, f"{y_big} + big_l", zc, "big_w"), drop(y_small, f"{y_small} + small_l", zc, "small_w")]
    for poly in polys:
        add("sketch.line", points=[list(p) for p in poly], closed=True, infer=False)
    for k, w in enumerate(["big_w", "small_w", "big_w", "small_w"]):
        n = 5 * k     # line ids before this hole
        add("sketch.fillet", points=[f"l{n + 4}.end", f"l{n + 5}.end"], radius=f"{w} * 0.45")
        add("sketch.fillet", points=[f"l{n + 1}.end", f"l{n + 3}.end"], radius=f"{w} / 4")
    add("sketch.finish")
    add("solid.extrude", distance=f"{FREE_X0} - side_x + 2 * fin_lip + 2 * eps", start_offset="side_x - fin_lip - eps", operation="cut",
        targets=[L], profiles="all", name="Kabelloecher")


def cable_notches():
    """Notches through the left half's spine, open to the back, so plugged cables drop in from
    behind; centred between the outer dovetails' slots and the gussets of the free space."""
    zc = "(dt_e + dt_root / 2 + dt_s * (dt_d + dt_c) + dt_cv + plate_t + bay_h - gus_c) / 2"
    for k, z in enumerate([zc, f"panel_h - ({zc})"]):
        box(L, ["mid - spine_t - eps", "depth - notch_l", f"{z} - notch_h / 2"], ["spine_t + 2 * eps", "notch_l + eps", "notch_h"],
            op="cut", name=f"Kabelschlitz{k}")


def latches():
    """Per level a screw boss behind the faceplate beside the bay and a latch, drawn locked: it
    reaches over the flat part of the Mac's front, turned by 180 degrees it lies over the faceplate."""
    px = f"{FREE_X0} + latch_px"
    reach = "side_x + wall_t + fit + mac_w - mac_r - latch_over"
    for k, zf in enumerate(FLOORS):
        pz = f"{zf} + latch_z"
        name = f"Riegel_{k + 1}"
        add("solid.box", length=f"{px} - ({reach})", width="latch_t", height="latch_w",
            corner=[reach, "0 mm - latch_t", f"{pz} - latch_w / 2"], body_name=name)
        for x in (reach, px):
            add("solid.cylinder", diameter="latch_w", height="latch_t", axis="Y", base=[x, "0 mm - latch_t", pz],
                operation="join", targets=[name])
        add("solid.cylinder", diameter="latch_hole", height="latch_t + 2 * eps", axis="Y",
            base=[px, "0 mm - latch_t - eps", pz], operation="cut", targets=[name])
        # boss: revolved, starting inside the faceplate, its end rounded in the sketch; the foot
        # fillet comes last (fillets())
        add("sketch.create", plane="XY", offset=pz)
        add("sketch.line", points=[[px, "face_t / 2"], [f"{px} + boss_d / 2", "face_t / 2"],
                                   [f"{px} + boss_d / 2", "face_t + boss_l"], [px, "face_t + boss_l"]], closed=True, infer=False)
        add("sketch.fillet", points=["l2.end"], radius="boss_end_r")
        add("sketch.finish")
        add("solid.revolve", axis="l4", operation="join", targets=[L], name=f"Dom{k + 1}")
        add("solid.cylinder", diameter="screw_core", height="face_t + boss_l", axis="Y", base=[px, "0 mm - eps", pz],
            operation="cut", targets=[L])


def bay_features(body, xl):
    """Rear stop (right) and power button notch (left) of both bays of a half; xl = bay's left wall."""
    for zf in FLOORS:
        # 45 degree stop: the slope starts foot_h in front of the Mac's back, so it meets the
        # housing's bottom edge, never the foot
        y_s = "mac_y + mac_w - foot_h"
        add("sketch.create", plane=YZ)
        y_e = "depth - stop_back"
        # the slope runs on into the plate, so the stop starts inside material; its foot fillet
        # comes last (fillets())
        add("sketch.line", points=[[f"{y_s} - plate_t / 2", f"{zf} - plate_t / 2"], [y_e, f"{zf} - plate_t / 2"],
                                   [y_e, f"{zf} + stop_h - stop_back"]], closed=True, infer=False)
        add("sketch.fillet", points=["l2.end"], radius="stop_r")
        add("sketch.finish")
        add("solid.extrude", distance="stop_w", start_offset=f"{xl} + fit + mac_w - mac_r - stop_w",
            operation="join", targets=[body])
        # power button: slot with a round end, open to the back, clear of the wall and its fillets
        cx = f"{xl} + fit + btn_x"
        add("sketch.create", plane="XY", offset=f"{zf} - plate_t - eps")
        yc = "mac_y + mac_w - btn_l + btn_w / 2"
        add("sketch.line", points=[[f"{cx} + btn_w / 2", yc], [f"{cx} + btn_w / 2", "depth + eps"],
                                   [f"{cx} - btn_w / 2", "depth + eps"], [f"{cx} - btn_w / 2", yc]], infer=False)
        add("sketch.arc.center_point", center=[cx, yc], start=[f"{cx} - btn_w / 2", yc], end=[f"{cx} + btn_w / 2", yc])
        add("sketch.finish")
        add("solid.extrude", distance="plate_t + 2 * eps", operation="cut", targets=[body], profiles="all", name="Knopf")


def dovetails():
    """Tabs on the left half, slots (closed at the back) in the right half. The slot is the tab
    offset by dt_c square to each face; both start eps inside the left half, on the flank's line."""
    zs = ["dt_e", "panel_h / 2", "panel_h - dt_e"]
    sketch(XZ, [[("mid - eps", f"{z} - dt_root / 2 + dt_s * eps"), ("mid + dt_d", f"{z} - dt_tip / 2"),
                 ("mid + dt_d", f"{z} + dt_tip / 2"), ("mid - eps", f"{z} + dt_root / 2 - dt_s * eps")] for z in zs])
    add("solid.extrude", distance="depth - dt_cap", direction="negative", operation="join", targets=[L],
        profiles="all", name="Schwalbe_Zapfen")
    sketch(XZ, [[("mid - eps", f"{z} - dt_root / 2 + dt_s * eps - dt_cv"), ("mid + dt_d + dt_c", f"{z} - dt_root / 2 - dt_s * (dt_d + dt_c) - dt_cv"),
                 ("mid + dt_d + dt_c", f"{z} + dt_root / 2 + dt_s * (dt_d + dt_c) + dt_cv"), ("mid - eps", f"{z} + dt_root / 2 - dt_s * eps + dt_cv")]
                for z in zs])
    add("solid.extrude", distance="depth - dt_cap + eps", start_offset="eps", direction="negative", operation="cut",
        targets=[R], profiles="all", name="Schwalbe_Nut")


def fillet(body, radius, points, name):
    add("solid.fillet", body=body, radius=radius, edges=[[round(v, 4) for v in pt] for pt in points], name=name)


def fillets():
    """Last in the timeline, after every join and cut: the roundings no sketch can carry. Edges
    are picked at the default parameter values and mirrored about mid for the right half."""
    mx = lambda x, side: x if side == L else ev("panel_w") - x
    zs = [ev(f"{zf} + latch_z") for zf in FLOORS]
    px = ev(f"{FREE_X0} + latch_px")
    y_s = ev("mac_y + mac_w - foot_h")
    rib_corners = [[x, ev("depth + fin_l"), z] for x in (ev("side_x + wall_t / 2"), ev(f"{BAY_X1} + bay_wall_t / 2"))
                   for z in (ev("fin_inset"), ev("panel_h - fin_inset"))]
    for side, xl in ((L, ev("side_x + wall_t")), (R, ev("panel_w - side_x - wall_t - bay_w"))):
        tag = "L" if side == L else "R"
        fillet(side, "boss_r", [[mx(px, side), ev("face_t"), z + ev("boss_d / 2")] for z in zs], f"Dom_Fuss_{tag}")
        fillet(side, "fin_r", [[mx(x, side), y, z] for x, y, z in rib_corners], f"Kabelrippe_Ecken_{tag}")
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
    half()
    bay_wall_slots()
    fins()
    cable_notches()
    latches()
    add("solid.mirror", bodies=[L, "Riegel_1", "Riegel_2"], plane={"origin": ["mid", "0 mm", "0 mm"], "normal": [1, 0, 0]})
    add("body.rename", body=f"{L} (2)", name=R)
    add("body.rename", body="Riegel_1 (2)", name="Riegel_3")
    add("body.rename", body="Riegel_2 (2)", name="Riegel_4")
    bay_features(L, "side_x + wall_t")
    bay_features(R, "panel_w - side_x - wall_t - bay_w")
    dovetails()
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
