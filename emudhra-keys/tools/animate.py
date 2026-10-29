"""Renders how a number goes onto its mount: images/mount.mp4 and images/mount.gif.
The number is cut open along the rail's axis: it comes to the wall with the rail in its pocket,
then slides down until the rail wedges in the dovetail. Frames are SolidCraft snapshots of
cad/<key>.solidcraft with the number moved, the scene turned so the wall stands upright.

Usage: python -I animate.py [KEY]   (after make.py; needs solidcraft-cli, ffmpeg)
"""
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
from make import ROOT, WORK, evaluate  # noqa: E402

FPS = 30
AWAY = 70.0   # mm the number starts off the wall


def ease(t):
    return t * t * (3 - 2 * t)


def timeline(slide):
    """(dy, dz) of the number per frame: hold, onto the wall, hold, slide down, hold."""
    frames = [(slide, AWAY)] * 15
    frames += [(slide, AWAY * (1 - ease(i / 44))) for i in range(45)]
    frames += [(slide, 0.0)] * 15
    frames += [(slide * (1 - ease(i / 44)), 0.0) for i in range(45)]
    frames += [(0.0, 0.0)] * 40
    return frames


def frame(key, n, dy, dz, camera, out_dir, mx):
    """Renders frame n with the number moved by dy (up the wall) and dz (off it), cut open left of
    the rail's axis mx so the slot shows."""
    scene = [
        {"command": "solid.box", "params": {"length": 420, "width": 300, "height": 4, "corner": [-210, -150, -4],
                                            "operation": "new", "body_name": "Wall"}},
        {"command": "solid.move", "params": {"bodies": ["Number"], "translate": [0, dy, dz]}},
        {"command": "appearance.assign", "params": {"bodies": ["Wall"], "color": "#e9e6e1"}},
        {"command": "appearance.assign", "params": {"bodies": ["Mount"], "color": "#e8772e"}},
        {"command": "appearance.assign", "params": {"bodies": ["Number"], "color": "#3a3d42"}},
        # +Y (up the wall) becomes the view's up, the wall's normal points at the camera's side
        {"command": "solid.move", "params": {"bodies": ["Wall", "Mount", "Number"], "axis": [1, 0, 0], "angle": "90 deg"}},
        # cut open left of the rail's axis (X is unchanged by the turn); the pieces right of it may part
        {"command": "solid.box", "params": {"length": 400, "width": 400, "height": 400, "corner": [mx - 400, -200, -200],
                                            "operation": "cut", "targets": ["Number"]}},
    ]
    path = os.path.join(out_dir, f"s{n:04d}.json")
    json.dump({"commands": scene}, open(path, "w"))
    subprocess.run(["solidcraft-cli", "snapshot", path, "--in", os.path.join(ROOT, "cad", f"{key}.solidcraft"),
                    "--out", os.path.join(out_dir, f"f{n:04d}.png"), "--width", "960", "--height", "720",
                    "--camera", json.dumps(camera), "--no-grid", "--no-axes"], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    key = int(sys.argv[1]) if len(sys.argv) > 1 else 237
    V = build.values()
    slide = V["rail_l"] + V["c"]   # from the pocket to where the rail wedges
    out_dir = os.path.join(WORK, "anim")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    mx = next(p["value"] for p in evaluate(os.path.join(ROOT, "cad", f"{key}.solidcraft"))["params"] if p["name"] == "mx")
    camera = {"target": [mx + 15, -20, 30], "yaw": 1.25, "pitch": 0.25, "distance": 210}
    frames = timeline(slide)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda a: frame(key, a[0], a[1][0], a[1][1], camera, out_dir, mx), enumerate(frames)))
    mp4 = os.path.join(ROOT, "images", "mount.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(out_dir, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", mp4], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
                    "fps=15,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse",
                    os.path.join(ROOT, "images", "mount.gif")], check=True)
    print(mp4)
