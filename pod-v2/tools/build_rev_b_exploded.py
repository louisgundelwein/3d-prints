"""Build the Rev B exploded assembly from a populated KiCad STEP export."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile


REV_B = Path(__file__).resolve().parents[1] / "rev-b"
PCB = REV_B / "pcb" / "Pod-B-populated.step"
CAMERA = {"target": [36, -50, 102], "yaw": 0.54, "pitch": 0.30, "distance": 405}


def commands():
    """Add the enclosure concept around the actual board and purchased modules."""
    operations = []
    variables = {
        "case_w": ("82 mm", "Estimate: enclosure width"),
        "case_h": ("119 mm", "Estimate: enclosure height with Wi-Fi antenna clearance"),
        "wall": ("2.5 mm", "Estimate: enclosure wall"),
        "rear_h": ("24 mm", "Estimate: tray depth"),
        "scan_z": ("49 mm", "Exploded QR engine elevation"),
        "pcb_z": ("98 mm", "Exploded populated PCB elevation"),
        "front_modules_z": ("137 mm", "Exploded light guide and NFC elevation"),
        "face_z": ("181 mm", "Exploded front cover elevation"),
    }

    def add(command, **params):
        operations.append({"command": command, "params": params})

    def box(name, corner, size, target=None):
        operation = {"operation": "cut", "targets": [target]} if target else {"body_name": name}
        add("solid.box", name=name, corner=corner, length=size[0], width=size[1], height=size[2], **operation)

    def cylinder(name, base, diameter, height, target=None):
        operation = {"operation": "cut", "targets": [target]} if target else {"body_name": name}
        add("solid.cylinder", name=name, base=base, diameter=diameter, height=height, **operation)

    def color(name, hex_color, opacity=1):
        add("appearance.assign", bodies=[name], color=hex_color, opacity=opacity)

    for name, (expression, note) in variables.items():
        add("parameters.add", name=name, expression=expression, comment=note)

    x0, y0 = "(72 mm - case_w) / 2", "-105 mm"
    inner = [f"{x0} + wall", f"{y0} + wall"]
    rear = "Wandhalter"
    box(rear, [x0, y0, 0], ["case_w", "case_h", "rear_h"])
    box("Hohlraum", [*inner, "wall"], ["case_w - 2 * wall", "case_h - 2 * wall", "rear_h"], rear)
    box("Kabelauslass", [28, f"{y0} - 1 mm", "wall + 1 mm"], [16, "wall + 2 mm", "rear_h"], rear)
    for x in (4, 68):
        for y in (-4, -96):
            add("solid.cylinder", name="Platinenauflage", base=[x, y, "wall / 2"], diameter=6.5, height=15,
                operation="join", targets=[rear])
            cylinder("Auflagebohrung", [x, y, "wall / 2"], 2.5, 16, rear)
    color(rear, "#263648")

    scanner = "Newland EM3080-W V2 · Bauraum"
    box(scanner, [28.25, -34.85, "scan_z"], [15.5, 9.7, 13.9])
    cylinder("Scanneroptik", [38.1, -31.15, "scan_z + 13.9 mm"], 4.8, 0.5)
    box("Scanbeleuchtung", [30.0, -32.9, "scan_z + 13.9 mm"], [3, 3.5, 0.35])
    color(scanner, "#262b35")
    color("Scanneroptik", "#111a2a")
    color("Scanbeleuchtung", "#f9e6a7")

    board = "Rev B · bestückte KiCad-Platine"
    add("file.insert_step", name=board, path=str(PCB))
    add("occurrence.move", occurrence=board, translate=[0, 0, "pcb_z"], move_grounded=True)

    nfc = "ELECHOUSE PN7160 · Bauraum"
    box(nfc, [14.65, -96.55, "front_modules_z"], [42.7, 40.1, 1.6])
    box("NFC-Anschluss · Bauraum", [16.5, -61, "front_modules_z + 1.6 mm"], [11, 4, 3])
    color(nfc, "#3a5982")
    color("NFC-Anschluss · Bauraum", "#e9e3d1")
    for index in range(3):
        name = f"NFC-Windung · Darstellung {index + 1}"
        inset = index * 1.7
        x, y = 19 + inset, -91 + inset
        width, depth = 34 - 2 * inset, 26 - 2 * inset
        box(name, [x, y, "front_modules_z + 1.6 mm"], [width, depth, 0.07])
        box("Windung innen", [x + 0.6, y + 0.6, "front_modules_z + 1.5 mm"], [width - 1.2, depth - 1.2, 0.3], name)
        box("Windung offen", [33, y - 0.2, "front_modules_z + 1.5 mm"], [6, 1, 0.3], name)
        color(name, "#dda469")

    diffuser = "Lichtleitring"
    cylinder(diffuser, [36, -30, "front_modules_z"], 43, 2)
    cylinder("Lichtleiter innen", [36, -30, "front_modules_z - 1 mm"], 31, 4, diffuser)
    color(diffuser, "#7be0dc", 0.75)

    face = "Frontdeckel"
    box(face, [x0, y0, "face_z"], ["case_w", "case_h", 6])
    box("Deckel innen", [*inner, "face_z - 1 mm"], ["case_w - 2 * wall", "case_h - 2 * wall", 4.5], face)
    cylinder("Öffnung für Lichtleiter und Blende", [36, -30, "face_z - 1 mm"], 43.5, 8, face)
    bezel = "Lichtdichte Scannerblende"
    cylinder(bezel, [36, -30, "face_z + 3.5 mm"], 30.7, 2.5)
    box("Scanöffnung", [27.25, -36, "face_z + 2 mm"], [17.5, 12, 6], bezel)
    color(face, "#405777")
    color(bezel, "#1f2733")
    add("view.save", name="Explosionsansicht", camera=CAMERA)
    return operations


def main():
    """Write the SolidCraft document, or emit commands for its live application."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", action="store_true")
    args = parser.parse_args()
    model = json.dumps({"commands": commands()}, ensure_ascii=False)
    if args.commands:
        print(model)
        return
    with tempfile.TemporaryDirectory(prefix="pod-rev-b-explosion-") as directory:
        source = Path(directory) / "build.json"
        source.write_text(model, encoding="utf-8")
        subprocess.run([
            "solidcraft-cli", "run", str(source), "--param-check", "strict", "--quiet",
            "--save", str(REV_B / "pod-v2-rev-b-exploded.sc"),
        ], check=True)


if __name__ == "__main__":
    main()
