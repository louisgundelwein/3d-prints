"""Generate a SolidCraft assembly of the actual PCB and concept enclosure parts."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile


POD = Path(__file__).resolve().parents[1]
VIEW = {"target": [32.5, -22, 64], "yaw": 0.64, "pitch": 0.35, "distance": 280}


def commands():
    """Model the enclosure parts and space them along the assembly axis."""
    steps = []
    parameters = {
        "case_w": ("81 mm", "Concept estimate, width"),
        "case_d": ("64 mm", "Concept estimate, depth"),
        "wall": ("2.5 mm", "Concept estimate, wall thickness"),
        "rear_h": ("30 mm", "Concept estimate, rear tray height"),
        "board_z": ("54 mm", "Exploded PCB elevation"),
        "scanner_z": ("88 mm", "Exploded scanner elevation"),
        "front_z": ("124 mm", "Exploded front elevation"),
        "scanner_w": ("53.3 mm", "Waveshare 14810 published footprint width"),
        "scanner_d": ("21.4 mm", "Waveshare 14810 published footprint depth"),
        "scanner_h": ("13 mm", "Estimate, simplified module envelope height"),
    }

    def add(command, **params):
        steps.append({"command": command, "params": params})

    def box(name, corner, size, cut=None):
        extra = {"targets": [cut], "operation": "cut"} if cut else {"body_name": name}
        add("solid.box", name=name, corner=corner, length=size[0], width=size[1], height=size[2], **extra)

    for name, (value, note) in parameters.items():
        add("parameters.add", name=name, expression=value, comment=note)
    x0, y0 = "(65 mm - case_w) / 2", "(-45 mm - case_d) / 2"
    inner_x, inner_y = f"{x0} + wall", f"{y0} + wall"
    rear = "Wandhalter"
    front = "Frontdeckel"
    scanner = "QR-Scanner (Bauraummodell)"
    box(rear, [x0, y0, 0], ["case_w", "case_d", "rear_h"])
    box("Innenraum des Wandhalters", [inner_x, inner_y, "wall"], ["case_w - 2 * wall", "case_d - 2 * wall", "rear_h"], rear)
    box("Kabeldurchführung", ["27 mm", f"{y0} - 1 mm", "wall + 1 mm"], ["11 mm", "wall + 2 mm", "rear_h"], rear)
    for x, y in [(3.5, -3.5), (61.5, -3.5), (3.5, -41.5), (61.5, -41.5)]:
        add("solid.cylinder", name="Platinenauflage", base=[x, y, "wall / 2"], diameter="6 mm",
            height="wall / 2 + 4 mm", operation="join", targets=[rear])
        add("solid.cylinder", name="Bohrung in Platinenauflage", base=[x, y, "wall / 2"], diameter="2.5 mm",
            height="wall / 2 + 5 mm", operation="cut", targets=[rear])
    add("appearance.assign", bodies=[rear], color="#233246")

    add("file.insert_step", path=str(POD / "pcb" / "Pod-A.step"), name="Rev A · bestückte Platine",
        matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, "board_z"])
    box(scanner, ["(65 mm - scanner_w) / 2", "-45 mm", "scanner_z"], ["scanner_w", "scanner_d", "scanner_h"])
    box("Optikfenster", ["24 mm", "-40 mm", "scanner_z + scanner_h"], ["17 mm", "11 mm", "0.8 mm"])
    add("appearance.assign", bodies=[scanner], color="#3c4653")
    add("appearance.assign", bodies=["Optikfenster"], color="#111e2a")
    box(front, [x0, y0, "front_z"], ["case_w", "case_d", "6 mm"])
    box("Aussparung unter dem Deckel", [inner_x, inner_y, "front_z - 1 mm"],
        ["case_w - 2 * wall", "case_d - 2 * wall", "7 mm - wall"], front)
    box("Scanausschnitt", ["18 mm", "-44 mm", "front_z - 1 mm"], ["29 mm", "18 mm", "8 mm"], front)
    add("solid.cylinder", name="LED-Öffnung", diameter="6 mm", base=[32.5, -22, "front_z - 1 mm"],
        height="8 mm", operation="cut", targets=[front])
    add("appearance.assign", bodies=[front], color="#405674")
    add("view.save", name="Explosionsansicht", camera=VIEW)
    return steps


def main():
    """Write a portable SolidCraft file, or emit the commands for the live GUI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", action="store_true")
    args = parser.parse_args()
    script = json.dumps({"commands": commands()}, ensure_ascii=False)
    if args.commands:
        print(script)
        return
    with tempfile.TemporaryDirectory(prefix="pod-explosion-") as temporary:
        source = Path(temporary) / "build.json"
        source.write_text(script, encoding="utf-8")
        subprocess.run([
            "solidcraft-cli", "run", str(source), "--param-check", "strict", "--quiet",
            "--save", str(POD / "cad" / "pod-v2-exploded.sc"),
        ], check=True)


if __name__ == "__main__":
    main()
