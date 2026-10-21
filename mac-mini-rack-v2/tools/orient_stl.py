"""Rotates a binary STL into its print orientation and puts it on z = 0.

Usage: python -I orient_stl.py IN.stl OUT.stl R  where R is 9 comma-separated numbers (row-major
rotation matrix, rows = new X, new Y, new Z expressed in the model's axes).
"""
import struct, sys

src, dst, rot = sys.argv[1], sys.argv[2], [float(v) for v in sys.argv[3].split(",")]
R = [rot[0:3], rot[3:6], rot[6:9]]
det = (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
       + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))
if abs(det - 1) > 1e-9:
    raise SystemExit(f"not a rotation (det {det})")
data = open(src, "rb").read()
n = struct.unpack_from("<I", data, 80)[0]
if len(data) != 84 + 50 * n:
    raise SystemExit("not a binary STL")
tris = []
for i in range(n):
    v = struct.unpack_from("<12fH", data, 84 + 50 * i)
    pts = [tuple(sum(R[r][c] * v[3 * k + c] for c in range(3)) for r in range(3)) for k in range(4)]
    tris.append(pts)
lo = [min(p[a] for t in tris for p in t[1:]) for a in range(3)]
out = bytearray(80) + struct.pack("<I", n)
for t in tris:
    nrm = t[0]
    pts = [tuple(p[a] - lo[a] for a in range(3)) for p in t[1:]]
    out += struct.pack("<12fH", *nrm, *pts[0], *pts[1], *pts[2], 0)
open(dst, "wb").write(out)
hi = [max(p[a] for t in tris for p in t[1:]) - lo[a] for a in range(3)]
print(dst, "size", [round(h, 2) for h in hi])
