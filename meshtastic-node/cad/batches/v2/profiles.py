"""Sketch commands for the cavity-type outlines of the v2 case.

The outline is the rectangle [a, L-a] x [a, W-a] with a concave bite of
radius R around each corner column centre, blended into the walls by
fillet arcs of radius f (f=0: sharp). Used for the upper cavity, the
lower cavity (ledge), the mounting plate and the lid rim. Prints sketch
command lists; numbers only (SolidCraft 0.30.1 cannot fillet a plane
into a cylinder, so the blends are drawn).
"""
import math

L, W = 79.0, 60.0  # keep equal to case_length, case_width


def _bl_corner(a, R, f, c=6.0):
    """Points of the bottom-left corner, travelling counter-clockwise
    (down the left wall, round the column, along the bottom wall)."""
    segs = []
    if f > 0:
        px = a + f
        py = c + math.sqrt((R + f) ** 2 - (px - c) ** 2)
        q1 = (a, py)
        t1 = (c + R * (px - c) / (R + f), c + R * (py - c) / (R + f))
        v1 = (q1[0] - px, q1[1] - py)
        v2 = (t1[0] - px, t1[1] - py)
        s = (v1[0] + v2[0], v1[1] + v2[1])
        n = math.hypot(*s)
        m1 = (px + f * s[0] / n, py + f * s[1] / n)
        segs.append(("arc", q1, m1, t1))
    else:
        t1 = (a, c + math.sqrt(R * R - (a - c) ** 2))
        q1 = t1
    d = (c + R / math.sqrt(2), c + R / math.sqrt(2))
    t2 = (t1[1], t1[0])
    segs.append(("arc", t1, d, t2))
    if f > 0:
        m2 = (m1[1], m1[0])
        q2 = (q1[1], q1[0])
        segs.append(("arc", t2, m2, q2))
    return segs


def _map(segs, fx, fy, reverse):
    def p(pt):
        return (L - pt[0] if fx else pt[0], W - pt[1] if fy else pt[1])
    out = [(k, p(s), p(m), p(e)) for (k, s, m, e) in segs]
    if reverse:
        out = [(k, e, m, s) for (k, s, m, e) in reversed(out)]
    return out


def loop(a, R, f):
    """Closed outline as sketch commands (CCW)."""
    bl = _bl_corner(a, R, f)
    corners = [bl, _map(bl, True, False, True), _map(bl, True, True, False), _map(bl, False, True, True)]
    cmds = []
    r = lambda pt: [round(pt[0], 4), round(pt[1], 4)]
    for i, segs in enumerate(corners):
        for (_, s, m, e) in segs:
            cmds.append({"command": "sketch.arc.three_point", "params": {"start": r(s), "through": r(m), "end": r(e)}})
        nxt = corners[(i + 1) % 4][0][1]
        cmds.append({"command": "sketch.line", "params": {"points": [r(segs[-1][3]), r(nxt)]}})
    return cmds
