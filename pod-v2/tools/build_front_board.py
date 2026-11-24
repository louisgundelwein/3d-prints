"""Build the SolidCraft component placement study for the integrated front PCB."""

import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile


POD = Path(__file__).resolve().parents[1]
CENTER = [36, 70]
LED_COUNT = 12
LED_RADIUS = 18.5
FRONT = {"target": [36, 50, 0], "yaw": 0.26, "pitch": 1.28, "distance": 180}
REAR = {"target": [36, 50, 0], "yaw": 2.80, "pitch": -1.20, "distance": 175}


def commands():
    """Place the scanner between the front LEDs and the rear-mounted controller."""
    steps = []
    parameters = {
        "pcb_w": ("72 mm", "Estimate: front board width"),
        "pcb_h": ("100 mm", "Estimate: front board height"),
        "pcb_z": ("1.6 mm", "Nominal PCB thickness"),
        "scan_w": ("15.5 mm", "Newland EM3080-W V2 envelope width"),
        "scan_h": ("9.7 mm", "Newland EM3080-W V2 envelope height"),
        "scan_d": ("13.9 mm", "Newland EM3080-W V2 envelope depth"),
        "cut_w": ("17.5 mm", "Rev B KiCad optical window width"),
        "cut_h": ("12 mm", "Rev B KiCad optical window height"),
        "led_w": ("3.5 mm", "Estimate: RGB package width"),
        "led_z": ("1 mm", "Estimate: RGB package height"),
        "nfc_w": ("42.7 mm", "ELECHOUSE PN7160 module width"),
        "nfc_h": ("40.1 mm", "ELECHOUSE PN7160 module height"),
        "nfc_offset": ("3 mm", "Estimate: module elevation above host board"),
    }

    def add(command, **params):
        steps.append({"command": command, "params": params})

    def box(name, corner, size, targets=None):
        options = {"operation": "cut", "targets": targets} if targets else {"body_name": name}
        add("solid.box", name=name, corner=corner, length=size[0], width=size[1], height=size[2], **options)

    def color(bodies, value):
        add("appearance.assign", bodies=bodies, color=value)

    for name, (value, comment) in parameters.items():
        add("parameters.add", name=name, expression=value, comment=comment)

    board = "Frontplatine"
    box(board, [0, 0, 0], ["pcb_w", "pcb_h", "pcb_z"])
    box("Durchbruch QR", ["36 mm - cut_w / 2", "70 mm - cut_h / 2", -1],
        ["cut_w", "cut_h", "pcb_z + 2 mm"], [board])
    for x in ("4 mm", "pcb_w - 4 mm"):
        for y in ("4 mm", "pcb_h - 4 mm"):
            add("solid.cylinder", name="Montagebohrung", base=[x, y, -1], diameter=3.2,
                height="pcb_z + 2 mm", operation="cut", targets=[board])
    color([board], "#176652")

    scanner = "QR-Scanner · EM3080-W V2"
    box(scanner, ["36 mm - scan_w / 2", "70 mm - scan_h / 2", "pcb_z + 0.6 mm - scan_d"],
        ["scan_w", "scan_h", "scan_d"])
    box("QR-Optik", [36, 67.1, "pcb_z + 0.6 mm"], [4.8, 3.8, 0.2])
    box("Scanner-Beleuchtung", [30, 67.1, "pcb_z + 0.6 mm"], [3.5, 3.8, 0.2])
    color([scanner], "#263047")
    color(["QR-Optik"], "#111b2b")
    color(["Scanner-Beleuchtung"], "#fff4bc")

    leds = []
    for index in range(LED_COUNT):
        angle = index * math.tau / LED_COUNT
        x = CENTER[0] + LED_RADIUS * math.cos(angle)
        y = CENTER[1] + LED_RADIUS * math.sin(angle)
        name = f"RGB {index + 1:02}"
        box(name, [f"{x:.5f} mm - led_w / 2", f"{y:.5f} mm - led_w / 2", "pcb_z"],
            ["led_w", "led_w", "led_z"])
        leds.append(name)
    color(leds, "#c9fff0")
    diffuser = "Lichtleitring · Konzept"
    add("solid.cylinder", name=diffuser, body_name=diffuser, base=[36, 70, "pcb_z + led_z"],
        diameter=43, height=1.8)
    add("solid.cylinder", name="Innenöffnung Lichtleitring", base=[36, 70, "pcb_z + led_z - 1 mm"],
        diameter=31, height=3.8, operation="cut", targets=[diffuser])
    add("appearance.assign", bodies=[diffuser], color="#80ebdf", opacity=0.33)

    module = "NFC-Modul · ELECHOUSE PN7160"
    box(module, ["36 mm - nfc_w / 2", "23.5 mm - nfc_h / 2", "pcb_z + nfc_offset"],
        ["nfc_w", "nfc_h", "pcb_z"])
    color([module], "#294a72")
    coils = []
    for turn in range(3):
        inset = turn * 1.9
        x, y = 19 + inset, 8 + inset
        width, depth = 34 - 2 * inset, 30 - 2 * inset
        name = f"NFC-Antennenzone · Windung {turn + 1}"
        box(name, [x, y, "2 * pcb_z + nfc_offset"], [width, depth, 0.08])
        box(f"Antennenöffnung {turn + 1}", [x + 0.6, y + 0.6, "2 * pcb_z + nfc_offset - 0.1 mm"],
            [width - 1.2, depth - 1.2, 0.3], [name])
        box(f"Antennenanschluss {turn + 1}", [33, y - 0.1, "2 * pcb_z + nfc_offset - 0.1 mm"],
            [6, 0.85, 0.3], [name])
        coils.append(name)
    color(coils, "#e5a461")

    box("ESP32-C3 · Funkmodul", [29.4, 88.8, -2.4], [13.2, 16.6, 2.4])
    box("WLAN-Antenne · Modulüberstand", [29.4, 100, -2.65], [13.2, 5.4, 0.25])
    box("Relais · G5V-1", [53, 44, -10], [12.5, 7.5, 10])
    box("Scanner-Flexanschluss · Hirose", [32, 55, -2], [8, 4, 2])
    box("Versorgung · Platzhalter", [7, 44, -3], [11, 10, 3])
    box("5 V und Türkontakt · Platzhalter", [60, 12, -7], [10, 6, 7])
    color(["ESP32-C3 · Funkmodul"], "#a5b1bf")
    color(["WLAN-Antenne · Modulüberstand"], "#cc995e")
    color(["Relais · G5V-1", "Scanner-Flexanschluss · Hirose"], "#262e3e")
    color(["5 V und Türkontakt · Platzhalter"], "#4e86a2")
    add("view.save", name="Vorderseite", camera=FRONT)
    add("view.save", name="Rückseite", camera=REAR)
    return steps


def main():
    """Save the editable model, or output its commands for the SolidCraft GUI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", action="store_true")
    args = parser.parse_args()
    script = json.dumps({"commands": commands()}, ensure_ascii=False)
    if args.commands:
        print(script)
        return
    with tempfile.TemporaryDirectory(prefix="pod-front-board-") as directory:
        source = Path(directory) / "front.json"
        source.write_text(script, encoding="utf-8")
        subprocess.run([
            "solidcraft-cli", "run", str(source), "--param-check", "strict", "--quiet",
            "--save", str(POD / "rev-b" / "pod-v2-front-board.sc"),
        ], check=True)


if __name__ == "__main__":
    main()
