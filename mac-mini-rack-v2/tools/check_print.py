"""Lists the downward-facing areas of a binary STL in print orientation that need support or bridge.

Usage: python -I check_print.py PART.stl [max_angle_deg]

A face counts when it hangs more than max_angle_deg (default 45) from vertical and is not on the
bed. Connected faces are grouped; each group prints its bounding box, area and whether it is flat
(a bridge) or sloped (an overhang).
"""
import math
import struct
import sys

path = sys.argv[1]
limit = math.radians(float(sys.argv[2]) if len(sys.argv) > 2 else 45)
data = open(path, "rb").read()
n = struct.unpack_from("<I", data, 80)[0]
if len(data) != 84 + 50 * n:
    raise SystemExit("not a binary STL")
tris = []
for i in range(n):
    v = struct.unpack_from("<12f", data, 84 + 50 * i)
    a, b, c = v[3:6], v[6:9], v[9:12]
    u = [b[k] - a[k] for k in range(3)]
    w = [c[k] - a[k] for k in range(3)]
    nr = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    ln = math.sqrt(sum(x * x for x in nr))
    if ln == 0:
        continue    # zero-area triangle: no face to hang
    tris.append((a, b, c, [x / ln for x in nr], ln / 2))

hang = [t for t in tris if t[3][2] < -math.sin(limit) and min(p[2] for p in t[:3]) > 0.05]
# group triangles sharing a vertex
key = lambda p: tuple(round(x, 3) for x in p)
parent = list(range(len(hang)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


seen = {}
for i, t in enumerate(hang):
    for p in t[:3]:
        j = seen.setdefault(key(p), i)
        parent[find(i)] = find(j)
groups = {}
for i, t in enumerate(hang):
    groups.setdefault(find(i), []).append(t)
for g in sorted(groups.values(), key=lambda g: -sum(t[4] for t in g)):
    pts = [p for t in g for p in t[:3]]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    flat = all(t[3][2] < -0.999 for t in g)
    print(f"{'bridge ' if flat else 'overhang'} area {sum(t[4] for t in g):8.1f} mm2  "
          f"x {lo[0]:.1f}..{hi[0]:.1f}  y {lo[1]:.1f}..{hi[1]:.1f}  z {lo[2]:.1f}..{hi[2]:.1f}")
if not groups:
    print("no overhangs")
