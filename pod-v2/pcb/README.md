# Pod controller · Rev A

Open `Pod-A.kicad_pro` in KiCad 9. The two-layer board is routed. KiCad 9.0.9 reported zero ERC and DRC violations, zero unconnected pads and zero differences between the PCB and schematic. See [ERC](checks/ERC.rpt) and [DRC](checks/DRC.rpt). Physical bring-up, scanner compatibility and enclosure RF performance remain unverified.

## Wiring and programming

Pin 1 has a square pad. Signal directions below are from the controller. The 2.54 mm headers are unkeyed. Check connector orientation before applying power.

| Header | Pins in order | Connection |
| --- | --- | --- |
| J1 | 1 +5 V, 2 GND | Regulated isolated 5 V bench supply. Maintain at least 4.75 V at the board under load. |
| J2 | 1 +5 V, 2 GND, 3 TX, 4 RX | Scanner power and UART1. Connect TX to scanner RX and RX to scanner TX. Both data pins require 3.3 V logic. Verify the scanner cable pinout and output voltage first. |
| J3 | 1 COM, 2 NO | Optional voltage-free normally-open contact for a low-voltage signal circuit. |
| J4 | 1 GND, 2 TX, 3 RX | 3.3 V logic USB-to-UART adapter. Cross TX/RX, share ground, leave adapter power disconnected and supply J1. |

Hold BOOT (SW1), press and release RESET (SW2), then release BOOT to enter the serial loader. Reset again after programming. The 10 kΩ pull-ups on GPIO2/8/9 establish boot straps. EN has a 10 kΩ / 1 µF reset delay.

## Assembly and pin map

Order from [BOM.csv](BOM.csv). Populate all relay-option parts together for the switched output. An unpopulated relay section leaves J3 open. On a populated board GPIO3 drives the MOSFET through 100 Ω. A 10 kΩ gate-to-source resistor holds it off when the GPIO is high impedance. D2 clamps the coil turn-off pulse.

| Device | Physical pin assignments |
| --- | --- |
| ESP32-C3-MINI-1-N4X | Pad 3 = 3.3 V, 8 = EN. Pads 12/13/16 = GPIO0/1/10 for red/green/blue. Pads 18/19 = GPIO4/5 for scanner TX/RX. Pad 6 = GPIO3 relay. Pads 5/22/23 = GPIO2/8/9. Pads 31/30 = GPIO21/20 for programming TX/RX. Ground pads 1, 2, 11, 14 and 36–53 connect to GND. |
| TSR 1-2433 | 1 = +5 V, 2 = GND, 3 = +3.3 V. The 1 A buck supplies the controller. J2 draws directly from J1. Size the supply and harness for scanner peak current plus controller and relay demand. |
| RGB LED | 1 = red, 2 = common cathode, 3 = blue, 4 = green. Each color turns on with a high GPIO. Before placing the LED on the PCB, support the leads and form them from 1.27 mm to 2.159 mm pitch. Keep each bend at least 3 mm from the lens base. Set the final lens height using the enclosure. |
| G5V-1 DC5 | Coil 2/9, common 5/6, normally open 10, normally closed 1 left open. The 5 V coil draws 30 mA nominal. |
| AO3400A / 1N4148W | MOSFET gate/source/drain = 1/2/3. Diode band = cathode, pad 1, +5 V. |

## Mechanical fit

PCB 65 × 45 × 1.6 mm. Four unplated Ø3.2 mm mounting holes sit 3.5 mm from adjacent edges. In top-view board coordinates, X increases right and Y down. The antenna overhangs Y = 0 by 5.4 mm between X = 25.9 and 39.1 mm. Reserve open space around it and keep metal, wiring and the scanner away from the antenna. The LED lens center is (32.5, 22) mm.

[Populated STEP](Pod-A.step) and [placement CSV](placement.csv) use the top-left board origin with positive Y toward the antenna. Component coordinates are footprint anchors. The LED anchor is pin 1. The assembled model includes 25 components and represents nominal component bodies. Cable bend radii, mating plugs and formed lead heights need a physical fit check.

## First bench check

With power off, verify header polarity and check for shorts across the rails. Start with the scanner unplugged and J3 unloaded. Power J1, measure 3.3 V at U2 pin 3, and confirm J3 is open at reset. Flash through J4 and exercise the three colors and relay individually. Measure loaded J1 and 3.3 V during scanner startup and Wi-Fi transmission. Check TX/RX at J2 with a 3.3 V logic analyzer and test Wi-Fi with the enclosure closed.

## Component references

- [Espressif module datasheet, pin table and boot straps](https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html)
- [Traco TSR 1 series, model and terminal tables](https://www.tracopower.com/sites/default/files/products/datasheets/tsr1_datasheet.pdf)
- [Kingbright RGB LED, lead order and forming instructions](https://www.kingbrightusa.com/images/catalog/SPEC/WP154A4SUREQBFZGC.pdf)
- [Omron G5V-1, coil data and bottom-view contact diagram](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5v_1.pdf)
- [AO3400A gate rating and package](https://www.aosmd.com/sites/default/files/res/data_sheets/AO3400A.pdf)
- [Diodes Incorporated 1N4148W](https://www.diodes.com/part/view/1N4148W)
- [C&K KMR2 tactile switch](https://www.ckswitches.com/media/1479/kmr2.pdf)

The module symbol, footprint and STEP model come from [Espressif's KiCad library](https://github.com/espressif/kicad-libraries/tree/d5b68fd9269c639b3a60681e00b91df33b4db4a3). The local symbol expands the stacked ground pins for KiCad 9. The footprint removes the overhanging silkscreen and uses the bundled STEP path. See the [library license](models/LICENSE.md). Other library geometry comes from the [KiCad libraries](https://www.kicad.org/libraries/license/).
