# FRITZ!Box 7530 AX rack (work in progress)

1U module for a 10" LabRax rack that holds the bare PCB of a FRITZ!Box 7530 AX (case removed). The ports sit flush with the front panel.

Status: research only, nothing designed yet. Numbers marked *estimate* or *unverified* must be measured on the real board before printing.

## Goals

- Front is clean: LAN, DSL and phone jacks flush with the outside of the front panel.
- Power plugs in at the front, but the cable runs backwards through a hole or notch in the tray.
- USB (right side), TAE (left side) and the buttons (rear edge) do not need to reach the front. They stay reachable from the sides and back of the rack.
- LEDs are not needed at the front.
- Dust: openings that are not needed can be closed.

## Router

Read from the router on the LAN (`http://fritz.box/jason_boxinfo.xml`):

- Model: FRITZ!Box 7530 AX
- Hardware revision: HW 256
- FRITZ!OS: 8.25 (`256.08.25`)

## Board

Sources: [boxmatrix 7530ax](https://boxmatrix.info/wiki/7530ax) (photos and hardware table), [AVM product page](https://fritz.com/en/products/fritz-box-7530-ax-20002930).

| Item | Value | Source |
| --- | --- | --- |
| Case (W × D × H) | 200 × 152 × 45 mm | AVM |
| Power draw | 6 W average | AVM |
| PCB depth (USB edge) | about 128 mm | *estimate* from boxmatrix photo with ruler (Image85) |
| PCB width (port edge) | about 185 mm | *estimate* from photo proportions |
| Mounting holes | 4 | *unverified*, seen on photos, positions unknown |
| Case screws | 4 | boxmatrix |
| Cooling | passive, large aluminium heat spreader screwed over the SoC, no fan | boxmatrix photos |

Port layout (boxmatrix hardware table and photos):

| Edge | Contents | Position in rack |
| --- | --- | --- |
| Port edge (case back) | DSL (RJ45), FON1 (RJ11), LAN1–4 (RJ45), 12 V DC jack | front, flush with panel |
| Right side | USB-A 3.0 | right |
| Left side | TAE (FON1) | left |
| Opposite edge (case front) | 3 buttons (WLAN, DECT, Connect/WPS), LEDs | back |

Power supply: 12 V barrel plug. Third-party replacements are 12 V / 3 A, 5.5/2.5 mm. *Unverified*: read the label on the original adapter.

## Antennas

- WiFi: 3 antennas, all PCB traces (boxmatrix: "Murata, connecting 1 PCB-Trace"). Labels `2G_1`, `5G_1`, `5G_2` are printed at the button edge and corners.
- DECT: 2 PCB-trace antennas (boxmatrix).
- Nothing is glued to the case, so removing the case does not lose any antenna.
- With the ports at the front, the antennas end up at the back of the rack. A plastic rack is fine. Keep metal (screws, sheet metal, aluminium devices) away from the antenna edges and corners.

## Rack interface (LabRax, 10")

Source: [labrax-shelf](https://github.com/mix-forever/labrax-shelf) (`config.scad`, CC BY 4.0), which states compatibility with [Lab Rax](https://www.the-diy-life.com/introducing-lab-rax-a-3d-printable-modular-10-rack-system) by Michael Klements. *Unverified* against an original Lab Rax file.

| Item | Value |
| --- | --- |
| 1U | 44.45 mm |
| Panel width incl. ears | 250 mm |
| Hole spacing (centre to centre) | 236.525 mm |
| Holes per side in 1U | 3, at 6.35 / 22.225 / 38.1 mm from the bottom of the unit |
| Usable width between posts | 222 mm |
| Screws | M6 × 10 into M6 brass inserts (8 mm OD) |
| Mounting holes | 10 mm horizontal slots, about 6.3 mm wide |
| Panel thickness (labrax-shelf default) | 3 mm |
| Rack depth | unknown |

## Existing projects

Nothing found for a bare 7530 AX PCB, and no rack mount for the 7530 AX at all.

- [MakerWorld 1443771](https://makerworld.com/en/models/1443771): 10" bare-PCB bracket for the FRITZ!Box 7590. A search snippet claims it also fits the 7530 AX. *Unverified*, page not reachable.
- [Printables 173765](https://www.printables.com/model/173765-fritzbox-router-poe-switch-raspberry-19-2u-rack-mo): 19" 2U for older FRITZ!Box models.
- Rackmount.IT sells metal 19" kits for the 7530 and 7590.

## Design idea

- 1U front panel with LabRax ears, cutouts for DSL, FON1, LAN1–4 and the DC jack, sized so the jack faces are flush with the outside of the panel.
- Tray behind the panel; PCB screwed onto standoffs through its 4 holes. Plastic screws or standoffs near the antennas.
- Notch or hole in the tray next to the DC jack so the power cable bends back under or beside the board to the rear.
- Vent slots above and below the heat spreader.
- Parametric model like `mac-mini-rack-v2` (SolidCraft, `build.py` + `make.sh`).

## To measure

1. PCB outline (width, depth, thickness).
2. Positions and diameters of the 4 mounting holes.
3. For each jack on the port edge: distance from the left PCB corner, width, height above the PCB, and how far it sticks out over the edge.
4. Tallest part on top (heat spreader, capacitors) and on the bottom (solder joints, screws).
5. Power adapter label (voltage, current, plug size).
