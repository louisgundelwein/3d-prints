# Pod front carrier · Rev B prototype

Open **Pod-B.kicad_pro** with KiCad 9. Coordinates below are in millimetres from the upper left, viewed from the illuminated face. The two-layer carrier measures 72 × 100 × 1.6. LEDs D3–D14 face the user. The controller, power supply, relay and scanner ZIF sit behind them.

## Assembly and cables

| Connection | Pin order on carrier | Installation |
| --- | --- | --- |
| J1 | 1 regulated +5 V, 2 GND | Rear. Use an isolated, current-limited bench supply. Target 5.0 V at J1 under simultaneous load. |
| J2 | 2 +3.3 V, 3 GND, 4 host TX, 5 engine TX, 12 active-low trigger | Rear Hirose FH12-12S-0.5SH. Unlisted contacts open. J2 pin 1 is at (33.25,44.85). Fit the Newland NLS-EM3080-W V2 on a polymer cradle behind the 17.5 × 12 opening. SW3 triggers a scan. |
| J3 | 1 relay common, 2 normally open | Rear. For a low-voltage dry-contact signal input. |
| J4 | 1 GND, 2 host TX, 3 host RX | Rear. Use 3.3 V serial levels, cross TX/RX and power the carrier at J1. |
| J5 | 1 open, 2 SDA, 3 SCL, 4 IRQ, 5 VEN, 6 +3.3 V, 7 GND, 8 +5 V | Front JST GH SM08B-GHS-TB. Pin 1 is at (9.625,49.15). Mate with GHR-08V-S. Use the module's supplied cable at the opposite end. |

**Scanner flex.** Use 12 conductors, 0.50 mm pitch and a 0.30 mm reinforced end. Both sockets have bottom contacts. Choose contact exposure and length for the assembled fold so J2 pin 1 reaches engine pin 1. With both ends unpowered, verify continuity at contacts 1, 2, 3 and 12 before installing the engine. Never hot-plug. The mounting assumption is a dielectric cradle fixed to the two Ø2.2 holes at (23.5,30) and (48.5,30). They are carrier-to-cradle holes. The engine's own fasteners and optical axis must register to the cradle. Verify the fit, field of view, bend and latch access on a sample. [Newland integration guide, figures 2-1–3 and 4-1–4](https://newlandemea.katanapim.com/AttachmentDownload/Download/688?name=EM3080-W+V2_Integration+Guide_V1+2026.pdf) · [Hirose FH12](https://www.hirose.com/product/series/FH12)

**NFC assembly.** Retain the ELECHOUSE PN7160 I²C board on a dielectric cradle secured to the two lower carrier mounting holes, centered at (36,76.5), antenna parallel to the carrier. Its 42.70 × 40.10 outline fits inside a 46 × 43 copper and component keepout on both layers. Orient its cable outlet toward J5 and verify latch and cover clearance before ordering the harness. Wire numbered contact n of J5 to numbered contact n of the module, pins 2–8. Leave module pin 1 on its onboard pulldown. The keyed local harness accommodates the mounted module height, and different connector families. Check both pin numbers before crimping. J5 is a cable connection, with no rigid mating header. Keep wiring and metal beyond the antenna perimeter. VANT uses the vendor's 5 V PMU/TXLDO preset. [ELECHOUSE PN7160 I²C documentation, sections 3, 5–7](https://www.elechouse.com/docs/pn7160/)

## Power and control

The TRACO TSR 1-2433 supplies the ESP32-C3, scanner, receive buffer and NFC logic. The 5 V input feeds the LED chain, NFC RF stage and relay. Start with a 5 V / 2 A supply for bring-up. Confirm connector current, rail drop, ripple and temperature under sustained white LEDs, scanning, NFC polling, relay pull-in and Wi-Fi transmission.

| Function | ESP32-C3 GPIO |
| --- | --- |
| PN7160 SDA / SCL / IRQ / VEN | 0 / 1 / 6 / 7 |
| Scanner host TX / RX | 4 / 5 |
| LED data | 10 |
| Relay enable | 3 |
| Programming TX / RX | 21 / 20 |

Scanner and controller share 3.3 V. Keep GPIO4 low or high impedance until the scanner supply has settled. U4 restores the scanner TX logic high level before GPIO5. U3 translates LED data to 5 V. D3 receives DIN1 and each pixel feeds the next through D14. SW1 grounds BOOT and SW2 resets the controller. Hold SW1 while pressing and releasing SW2 for serial download. Firmware pin assignments and rail timing require a Rev B implementation.

## Release checks

Measure engine ripple at J2 (≤50 mV peak-to-peak, ≤30 mV recommended by Newland). Check scanner UART levels and enable timing during power-up and brownout. Test first and last pixel at full brightness, relay state at reset and optical isolation under a closed cover. Measure tap distance with target phones and fobs at full LED brightness and Wi-Fi load. Check radio range, scanner cradle alignment, cable retention and fastener clearances with the production enclosure.

[Espressif ESP32-C3-MINI-1](https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html) · [TRACO TSR 1](https://www.tracopower.com/sites/default/files/products/datasheets/tsr1_datasheet.pdf) · [TI scanner buffer](https://www.ti.com/lit/ds/symlink/sn74lv1t34.pdf) · [TI LED buffer](https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf) · [Worldsemi WS2812B-Mini-V6](https://www.world-semi.com/downloads/datasheets/en/ws2812b-mini-v6-1.0.pdf) · [Omron G5V-1](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5v_1.pdf)
