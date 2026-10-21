"""Export world-space animation meshes and an illustrative hardware STEP assembly.

Run from any directory: .venv/bin/python scripts/export_assembly.py
Install the pinned scripts/requirements.txt into a Python environment first.
The source CAD and print files are read-only inputs, never rewritten.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, TypedDict

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cad/assembly_with_mac_minis.step"
LINEAR_DEFLECTION_MM = 0.18
ANGULAR_DEFLECTION_RAD = 0.25
MAC_INDICES = (12, 13, 24, 25)
Side = Literal["left", "right"]
Kind = Literal["holder", "mac", "tpu", "screw", "insert"]
Point = tuple[float, float, float]


class Placement(TypedDict):
    name: str
    seatingPoint: Point
    axis: Point
    insertEntrance: Point
    screwSide: Side
    insertSide: Side


# P is the screw's under-head seating point; axis points from head toward tip.
def hardware_placements() -> list[Placement]:
    placements: list[Placement] = []
    for group in ("top", "bottom", "front"):
        for index, coordinate in enumerate(
            (20.0, 66.28, 112.56) if group == "front" else (30.0, 76.0, 122.0), 1
        ):
            if group == "top":
                seating, axis, entrance = (238.7, coordinate, 128.36), (0, 0, -1), (238.7, coordinate, 125.96)
            elif group == "bottom":
                seating, axis, entrance = (243.9, coordinate, 4.2), (0, 0, 1), (243.9, coordinate, 6.6)
            else:
                seating, axis, entrance = (241.3, 4.2, coordinate), (0, 1, 0), (241.3, 6.4, coordinate)
            placements.append({
                "name": f"{group}_{index}",
                "seatingPoint": seating,
                "axis": axis,
                "insertEntrance": entrance,
                "screwSide": "left" if group == "top" else "right",
                "insertSide": "right" if group == "top" else "left",
            })
    return placements


# Build a socket screw with a blind hex recess; threads are intentionally omitted.
def make_screw(placement: Placement) -> cq.Shape:
    p, d = cq.Vector(*placement["seatingPoint"]), cq.Vector(*placement["axis"])
    head_start = p - d * 4
    shaft = cq.Solid.makeCylinder(2, 10, p, d)
    head = cq.Solid.makeCylinder(3.5, 4, head_start, d)
    recess = cq.Workplane(cq.Plane(origin=head_start, normal=d)).polygon(6, 3.464101615).extrude(2).val()
    return shaft.fuse(head).cut(recess).clean()


# Build the assumed heat-set insert as a brass sleeve, without threads or knurling.
def make_insert(placement: Placement) -> cq.Shape:
    p, d = cq.Vector(*placement["insertEntrance"]), cq.Vector(*placement["axis"])
    return cq.Solid.makeCylinder(2.8, 8, p, d).cut(cq.Solid.makeCylinder(2, 8, p, d)).clean()


# Keep original face orientation and transforms through CadQuery's tessellator.
def mesh_part(shape: cq.Shape, name: str, kind: Kind, side: Side) -> dict[str, object]:
    vertices, triangles = shape.tessellate(LINEAR_DEFLECTION_MM, ANGULAR_DEFLECTION_RAD)
    if not vertices or not triangles:
        raise RuntimeError(f"Empty tessellation for {name}")
    positions = [round(value, 6) for vertex in vertices for value in vertex.toTuple()]
    minimum = [min(positions[axis::3]) for axis in range(3)]
    maximum = [max(positions[axis::3]) for axis in range(3)]
    return {
        "name": name, "kind": kind, "side": side,
        "positions": positions,
        "indices": [index for triangle in triangles for index in triangle],
        "centroid": [round(value, 6) for value in shape.Center().toTuple()],
        "bounds": {"min": minimum, "max": maximum},
    }


# Write strict JSON: non-finite geometry must fail instead of becoming invalid data.
def write_json(path: Path, data: object, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, allow_nan=False, indent=2 if pretty else None,
                               separators=None if pretty else (",", ":")) + "\n")


# Rebuild all three generated artifacts from the untouched source assembly.
def main() -> None:
    print(f"Importing {SOURCE.name}", flush=True)
    solids = cq.importers.importStep(str(SOURCE)).val().Solids()
    if len(solids) != 26:
        raise RuntimeError(f"Expected 26 source solids, found {len(solids)}; update classification explicitly")
    assembly = cq.Assembly(name="mac_mini_rack_with_illustrative_hardware")
    parts: list[dict[str, object]] = []
    mac_centers = {index: solids[index].Center().x for index in MAC_INDICES}
    for index, solid in enumerate(solids):
        side: Side = "left" if solid.Center().x < 241.3 else "right"
        direction = -1 if side == "left" else 1
        if index in (0, 1):
            kind: Kind = "holder"
            name = f"holder_{side}"
            detail: dict[str, object] = {"explodeDirection": [direction, 0, 0]}
        elif index in MAC_INDICES:
            kind = "mac"
            name = f"mac_{side}_{1 if index in (12, 13) else 2}"
            detail = {"explodeDirection": [0, -1, 0]}
        else:
            kind = "tpu"
            # These disjoint Z bands identify the existing floor, intake and top parts.
            bounds = solid.BoundingBox()
            if bounds.zmax < 5:
                role, explosion = "floor", [0, 0, -1]
            elif bounds.zmin > 118:
                role, explosion = "top", [0, 0, 1]
            elif bounds.zmin > 6 and bounds.zmax < 18:
                role, explosion = "intake", [direction, 0, -1]
            else:
                raise RuntimeError(f"Unexpected TPU position for source solid {index}")
            mac_index = min(mac_centers, key=lambda candidate: abs(mac_centers[candidate] - solid.Center().x))
            slot = 1 if mac_index in (12, 13) else 2
            name = f"tpu_{role}_{side}_{slot}_solid_{index:02d}"
            detail = {"role": role, "macName": f"mac_{side}_{slot}", "explodeDirection": explosion}
        part = mesh_part(solid, name, kind, side)
        part.update({"sourceSolidIndex": index, **detail})
        parts.append(part)
        assembly.add(solid, name=name)
        print(f"Meshed {name}", flush=True)

    placements = hardware_placements()
    for placement in placements:
        for hardware_kind in ("screw", "insert"):
            hardware_side = placement["screwSide"] if hardware_kind == "screw" else placement["insertSide"]
            shape = make_screw(placement) if hardware_kind == "screw" else make_insert(placement)
            name = f"{hardware_kind}_{placement['name']}"
            part = mesh_part(shape, name, hardware_kind, hardware_side)
            part.update({
                "illustrative": True, "placement": placement["name"],
                "axis": placement["axis"],
                "seatingPoint": placement["seatingPoint"],
                "insertEntrance": placement["insertEntrance"],
                "explodeDirection": [-value for value in placement["axis"]],
                "attachedTo": f"holder_{hardware_side}",
            })
            parts.append(part)
            color = cq.Color(0.28, 0.29, 0.31) if hardware_kind == "screw" else cq.Color(0.72, 0.51, 0.20)
            assembly.add(shape, name=name, color=color)

    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    common = {
        "schemaVersion": 1, "units": "mm",
        "coordinateSystem": {"x": "left-right", "y": "front-rear", "z": "up", "handedness": "right"},
        "source": {"path": "cad/assembly_with_mac_minis.step", "sha256": source_hash, "solidCount": 26},
    }
    write_json(ROOT / "video/assets/assembly.json", {
        **common,
        "mesh": {"linearDeflectionMm": LINEAR_DEFLECTION_MM, "angularDeflectionRad": ANGULAR_DEFLECTION_RAD,
                 "positions": "flat XYZ in original CAD world coordinates; no centering",
                 "indices": "flat zero-based triangle indices; CAD face winding preserved",
                 "explodeDirection": "suggested translation direction in CAD coordinates; normalize before use",
                 "bounds": "axis-aligned bounds computed from tessellated positions"},
        "parts": parts,
    })
    write_json(ROOT / "cad/hardware.json", {
        **common, "illustrative": True,
        "assumptions": [
            "Hardware geometry is illustrative for orbit and exploded animation; fit is not validated.",
            "M4x10 screws: 4 mm shaft diameter, 10 mm under-head length, 7 mm head diameter, 4 mm head height.",
            "Blind hex recess: 3 mm across flats, 2 mm deep. Screw threads and edge chamfers omitted.",
            "Assumed brass heat-set inserts: 5.6 mm OD, 8 mm length, 4 mm bore. Threads and knurling omitted.",
            "P is under-head seating; D is head-to-tip. Head occupies P-4D through P; shaft P through P+10D.",
            "Insert extends from its entrance along D. Screw withdrawal and suggested insert explosion are -D.",
            "Top screws attach to left holder and inserts to right; bottom/front screws attach to right and inserts to left.",
        ],
        "counts": {"screws": 9, "inserts": 9}, "placements": placements,
    }, pretty=True)
    assembly.export(str(ROOT / "cad/assembly_with_hardware.step"), exportType="STEP", mode="default", unit="MM")
    print(f"Built {len(parts)} named parts (26 original + 9 screws + 9 inserts); "
          f"{sum(len(part['indices']) // 3 for part in parts):,} triangles", flush=True)


if __name__ == "__main__":
    main()
