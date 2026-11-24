"""Build the editable SolidCraft mechanical reference for the Rev A PCB."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def board_commands():
    """Describe the board outline and its four mounting holes in millimetres."""
    parameters = {
        "board_length": ("65 mm", "Rev A PCB outline, X"),
        "board_width": ("45 mm", "Rev A PCB outline, Y"),
        "board_thickness": ("1.6 mm", "Nominal fabricated board thickness"),
        "mount_inset": ("3.5 mm", "Mounting-hole centre from either edge"),
        "mount_diameter": ("3.2 mm", "M3 screw clearance"),
        "cut_allowance": ("1 mm", "Extend drilling through both faces"),
        "radio_width": ("13.2 mm", "ESP32-C3-MINI-1 package dimension"),
        "radio_length": ("16.6 mm", "ESP32-C3-MINI-1 package dimension"),
        "radio_height": ("2.4 mm", "ESP32-C3-MINI-1 nominal package height"),
        "radio_overhang": ("5.4 mm", "Rev A antenna end beyond the board"),
    }
    commands = [
        {
            "command": "parameters.add",
            "params": {"name": name, "expression": value, "comment": note},
        }
        for name, (value, note) in parameters.items()
    ]
    commands.append({
        "command": "solid.box",
        "params": {
            "length": "board_length",
            "width": "board_width",
            "height": "board_thickness",
            "name": "PCB outline",
            "body_name": "PCB",
        },
    })
    for x in ("mount_inset", "board_length - mount_inset"):
        for y in ("mount_inset", "board_width - mount_inset"):
            commands.append({
                "command": "solid.cylinder",
                "params": {
                    "base": [x, y, "-cut_allowance"],
                    "diameter": "mount_diameter",
                    "height": "board_thickness + 2 * cut_allowance",
                    "operation": "cut",
                    "targets": ["PCB"],
                    "name": "M3 clearance",
                },
            })
    commands.append({
        "command": "appearance.assign",
        "params": {"bodies": ["PCB"], "color": "#177048"},
    })
    commands.extend([
        {
            "command": "solid.box",
            "params": {
                "corner": [
                    "(board_length - radio_width) / 2",
                    "board_width + radio_overhang - radio_length",
                    "board_thickness",
                ],
                "length": "radio_width",
                "width": "radio_length",
                "height": "radio_height",
                "name": "Wi-Fi module envelope",
                "body_name": "ESP32-C3-MINI-1",
            },
        },
        {
            "command": "appearance.assign",
            "params": {"bodies": ["ESP32-C3-MINI-1"], "color": "#a9b2b7"},
        },
    ])
    return commands


def main():
    """Save native CAD and STEP, or emit the same commands for the SolidCraft GUI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", action="store_true", help="Print the command script")
    args = parser.parse_args()
    script = json.dumps({"commands": board_commands()}, indent=2)
    if args.commands:
        print(script)
        return

    with tempfile.TemporaryDirectory(prefix="pod-v2-cad-") as directory:
        source = Path(directory) / "board.json"
        source.write_text(script, encoding="utf-8")
        subprocess.run(
            [
                "solidcraft-cli", "run", str(source), "--param-check", "strict",
                "--save", str(PROJECT / "cad" / "pod-v2-rev-a.sc"),
                "--out", str(PROJECT / "cad" / "pod-v2-rev-a.step"),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
