# Mac mini Rack v2

3D-printable 19" 3U rack mount for four Mac mini (M4), in two stacks of two, standing upright on their feet.

![Front](images/overview.png)
![Back](images/back.png)

## Parts

| File | Material | Qty |
| --- | --- | --- |
| `stl/Rack_links.stl` | PETG | 1 |
| `stl/Rack_rechts.stl` | PETG | 1 |
| `stl/Riegel_4x.stl` | PETG | 4 |

All parts are in print orientation, no supports. `orca/MacMini_Rack.3mf` is the OrcaSlicer project for a Bambu Lab P1S: plate 1 the left half (about 22.6 h, 1006 g), plate 2 the right half with the four latches (about 21.9 h, 967 g). `tools/orca_project.sh` rebuilds it from the STLs.

## Hardware

- 6× M6 rack screws with cage nuts
- 4× M4×16 screws with washers (latches; they cut their own thread)

## Assembly

1. Hold the right half in front of the left half and slide it backwards onto the dovetails until it stops.
2. Screw it into the rack. The rails keep the halves from sliding apart.
3. Slide each Mac in from the front until it touches the rear stop.
4. Screw on the latches. Turned towards the Mac they hold it in, turned the other way it slides out.

Cables: the outer walls and the walls beside the bays continue 70 mm behind the body, each with a large and a small cable hole per level (the large ones pass HDMI, power and LAN plugs). Slots in the walls beside the bays lead into the free space next to each stack. Notches open to the back run through both centre walls, so plugged cables drop in from behind.

Power button: each shelf has a round-ended slot under the Mac's rear left corner, open to the back.

## Model

`cad/rack.solidcraft` is the parametric SolidCraft design. Every length is a user parameter, e.g. `fit` (clearance around a Mac), `dt_c` (dovetail clearance), `plate_t`, `wall_t`. `tools/build.py` writes the command script that `solidcraft-cli run` turns into it; `--macs MAC.step` adds four Mac minis to check the fit. The Mac mini model is third-party and not included; the bays are sized from a 127 × 127 × 50.8 mm M4 model with its foot 6.35 mm high. `tools/check_print.py` lists the faces of an STL that need support or bridging.
