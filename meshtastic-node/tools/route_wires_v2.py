#!/usr/bin/env -S python3 -I
"""Route the 11 Dupont wires of the v2 case under the mounting plate.

Each wire is a Manhattan path on the floor:
  ESP pin -> X run -> Y run -> X run -> Y run -> X run -> radio pin
X runs lie at Z_X, Y runs at Z_Y, so X and Y runs may cross. A simulated
annealing search picks the free coordinates (xa, ym, xb) so that same-layer
runs keep GAP apart, bends and pin drops keep clear of other wires, and
paths stay off the corner column feet.

Usage: tools/route_wires_v2.py [restarts]  ->  cad/batches/v2/routes.json
"""
import itertools
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESP_X, ESP_Y = 26.5, 31.5
RADIO_X, RADIO_Y = 60.5, 30.0
Z_Y, Z_X = 3.35, 4.85          # wire centre heights (floor top 2.4, wire 1.1)
HOUSING_BOTTOM = 6.5
GAP = 1.45                     # centre distance for parallel runs
CORNER = 2.0                   # keep-out around bends and pin drops
COLUMNS = [(6, 6), (73, 6), (6, 54), (73, 54)]
COLUMN_KEEP = 7.0 + 0.55 + 0.3
BOUNDS = (5.0, 74.0, 5.0, 55.0)


def esp_pin(row, index):
    """World XY of ESP header pin; row 'left' (EN..VIN) or 'right' (D23..3V3)."""
    lx = 17.78 - (index - 1) * 2.54
    ly = 12.0 if row == "left" else -12.0
    return (ESP_X - ly, ESP_Y + lx)


def radio_pin(lx, ly):
    return (RADIO_X + lx, RADIO_Y + ly)


ESP = {
    "vcc": esp_pin("right", 15), "gnd": esp_pin("right", 14), "sck": esp_pin("right", 8),
    "miso": esp_pin("right", 6), "nss": esp_pin("right", 7), "nrst": esp_pin("right", 1),
    "mosi": esp_pin("left", 10), "dio1": esp_pin("left", 7), "busy": esp_pin("left", 6),
    "txen": esp_pin("left", 13), "rxen": esp_pin("left", 11),
}
RADIO = {
    "vcc": radio_pin(-11.69, -6.35), "gnd": radio_pin(-14.23, -6.35),
    "nss": radio_pin(-11.69, -3.81), "nrst": radio_pin(-14.23, -3.81),
    "mosi": radio_pin(-11.69, -1.27), "sck": radio_pin(-14.23, -1.27),
    "dio1": radio_pin(-11.69, 1.27), "miso": radio_pin(-14.23, 1.27),
    "busy": radio_pin(-14.23, 3.81),
    "rxen": radio_pin(-11.69, 6.35), "txen": radio_pin(-14.23, 6.35),
}
WIRES = list(ESP)
GRID = 0.4


def frange(a, b):
    n = int(round((b - a) / GRID))
    return [round(a + i * GRID, 3) for i in range(n + 1)]


ESP_LEFT_X, ESP_RIGHT_X = esp_pin("left", 1)[0], esp_pin("right", 1)[0]
RAD_NEAR_X, RAD_END_X = RADIO["vcc"][0], RADIO["gnd"][0]  # module-side row, board-end row
XA_LEFT = frange(ESP_LEFT_X + 2.4, ESP_RIGHT_X - 2.4)
XA_RIGHT = XA_LEFT + frange(ESP_RIGHT_X + 2.4, RAD_END_X - 2.4)
XB_END = frange(ESP_LEFT_X + 2.4, RAD_END_X - 2.4)      # approach board-end row from the left
XB_NEAR = frange(RAD_NEAR_X + 2.4, 72.0)                # approach module-side row from the right
YM = frange(6.0, 54.0)


def choices(w):
    xa = XA_LEFT if ESP[w][0] == ESP_LEFT_X else XA_RIGHT
    xb = XB_NEAR if RADIO[w][0] == RAD_NEAR_X else XB_END
    return xa, YM, xb


def poly(w, s):
    (x0, y0), (x1, y1) = ESP[w], RADIO[w]
    xa, ym, xb = s
    pts = [(x0, y0), (xa, y0), (xa, ym), (xb, ym), (xb, y1), (x1, y1)]
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, out[-1]) > 1e-9:
            out.append(p)
    # merge collinear points
    merged = [out[0]]
    for i in range(1, len(out) - 1):
        a, b, c = merged[-1], out[i], out[i + 1]
        if (abs(a[0] - b[0]) < 1e-9 and abs(b[0] - c[0]) < 1e-9) or (abs(a[1] - b[1]) < 1e-9 and abs(b[1] - c[1]) < 1e-9):
            continue
        merged.append(b)
    merged.append(out[-1])
    return merged


def segs(p):
    return [(p[i], p[i + 1], "Y" if abs(p[i][0] - p[i + 1][0]) < 1e-9 else "X") for i in range(len(p) - 1)]


def seg_dist(a, b, c, d):
    ax0, ax1 = sorted((a[0], b[0])); ay0, ay1 = sorted((a[1], b[1]))
    bx0, bx1 = sorted((c[0], d[0])); by0, by1 = sorted((c[1], d[1]))
    dx = max(0, bx0 - ax1, ax0 - bx1); dy = max(0, by0 - ay1, ay0 - by1)
    return math.hypot(dx, dy)


def pt_seg(p, a, b):
    return seg_dist(p, p, a, b)


def pair_cost(p, q):
    c = 0
    S, T = segs(p), segs(q)
    for a, b, o in S:
        for e, f, o2 in T:
            if o == o2 and seg_dist(a, b, e, f) < GAP:
                c += 1
    # bends and drops of one wire vs every run of the other
    for u, v in ((p, q), (q, p)):
        for k in u:
            for e, f, _ in segs(v):
                if pt_seg(k, e, f) < CORNER:
                    c += 1
    return c


def self_cost(p):
    c = 0
    sg = segs(p)
    for i, (a, b, _) in enumerate(sg):
        if math.dist(a, b) < 2.8:
            c += 2
        for col in COLUMNS:
            if pt_seg(col, a, b) < COLUMN_KEEP:
                c += 1
    for x, y in p:
        if not (BOUNDS[0] <= x <= BOUNDS[1] and BOUNDS[2] <= y <= BOUNDS[3]):
            c += 1
    return c


def total(state):
    P = {w: poly(w, state[w]) for w in WIRES}
    c = sum(pair_cost(P[u], P[v]) for u, v in itertools.combinations(WIRES, 2))
    c += sum(self_cost(P[w]) for w in WIRES)
    length = sum(math.dist(a, b) for w in WIRES for a, b, _ in segs(P[w]))
    return c, length, P


def search(restarts):
    best = None
    for r in range(restarts):
        random.seed(r)
        st = {w: [random.choice(ch) for ch in choices(w)] for w in WIRES}
        c, ln, _ = total(st)
        T = 3.0
        for _ in range(8000):
            w = random.choice(WIRES)
            k = random.randrange(3)
            old = st[w][k]
            st[w][k] = random.choice(choices(w)[k])
            c2, ln2, _ = total(st)
            score, score2 = c * 100 + ln * 0.01, c2 * 100 + ln2 * 0.01
            if score2 <= score or random.random() < math.exp((score - score2) / T):
                c, ln = c2, ln2
            else:
                st[w][k] = old
            T = max(0.02, T * 0.999)
        if best is None or (c, ln) < best[:2]:
            best = (c, ln, {k: v[:] for k, v in st.items()})
        print(f"restart {r}: cost {c} length {ln:.0f}", file=sys.stderr)
        if best[0] == 0 and r >= 4:
            break
    return best


def path3d(p):
    """Spline fit points: drop from the housing, layer changes at bends."""
    sg = segs(p)
    z = lambda o: Z_X if o == "X" else Z_Y
    unit = lambda a, b: ((b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b))
    pts = []
    x0, y0 = p[0]
    d = unit(sg[0][0], sg[0][1]); z0 = z(sg[0][2])
    pts += [(x0, y0, HOUSING_BOTTOM), (x0, y0, 5.6), (x0 + 0.6 * d[0], y0 + 0.6 * d[1], z0 + 0.3), (x0 + 1.4 * d[0], y0 + 1.4 * d[1], z0)]
    for i in range(len(sg)):
        a, b, o = sg[i]
        da = unit(a, b)
        if i > 0:
            pass
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if math.dist(a, b) > 4:
            pts.append((mid[0], mid[1], z(o)))
        if i < len(sg) - 1:
            db = unit(sg[i + 1][0], sg[i + 1][1]); zb = z(sg[i + 1][2]); za = z(o)
            pts += [(b[0] - 1.4 * da[0], b[1] - 1.4 * da[1], za),
                    (b[0] - 0.4 * da[0] + 0.4 * db[0], b[1] - 0.4 * da[1] + 0.4 * db[1], (za + zb) / 2),
                    (b[0] + 1.4 * db[0], b[1] + 1.4 * db[1], zb)]
    x1, y1 = p[-1]
    d = unit(sg[-1][0], sg[-1][1]); z1 = z(sg[-1][2])
    pts += [(x1 - 1.4 * d[0], y1 - 1.4 * d[1], z1), (x1 - 0.6 * d[0], y1 - 0.6 * d[1], z1 + 0.3), (x1, y1, 5.6), (x1, y1, HOUSING_BOTTOM)]
    return [[round(v, 3) for v in q] for q in pts]


if __name__ == "__main__":
    c, ln, st = search(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
    _, _, P = total(st)
    print(f"cost {c} length {ln:.1f}")
    out = {"cost": c, "state": st, "poly": P, "path3d": {w: path3d(P[w]) for w in WIRES},
           "esp_pins": ESP, "radio_pins": RADIO}
    json.dump(out, open(f"{ROOT}/cad/batches/v2/routes.json", "w"), indent=1)
    for w in WIRES:
        print(w, [tuple(round(v, 2) for v in pt) for pt in P[w]])
