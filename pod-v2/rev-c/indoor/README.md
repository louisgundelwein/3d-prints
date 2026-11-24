# Rev C indoor laboratory node

52 × 74 mm, two copper layers. Protected indoor bench prototype. The antenna overhangs the upper board edge by 5.4 mm; keep the antenna free of metal, enclosure hardware and wiring. Housing and RF performance require physical validation.

**Lab dummy load only until authorization is implemented and validated. Never connect live entry/access systems. Firmware, authorization, production installation and live entry testing are outside this design.**

## Wiring

| Connector | Pin | Connection |
|---|---|---|
| J1 | 1 / 2 | Regulated bench +5 V / GND |
| J2 Phoenix MKDS 5.08 mm | 1 | RS485 A, noninverting |
| J2 | 2 | RS485 B, inverting |
| J2 | 3 | GND reference, never supply power |
| J3 Phoenix MKDS 5.08 mm | 1 / 2 | Dry-contact COM / normally open NO |
| J4 UART0 | 1 / 2 / 3 | GND / GPIO21 TX / GPIO20 RX |
| J5 JST PH keyed | 1 / 2 | CR2032 primary battery positive / GND |

J1 uses a 2.54 mm pin header. Connect a separate regulated 5 V bench supply; do not backfeed through UART or RS485. UART logic is 3.3 V; cross TX/RX to the adapter. J3 carries low-voltage dummy loads only; no mains and no door strike. The relay coil has a flyback diode; external inductive loads require their own suppression.

The RS485 end has fixed 120 Ω termination across A/B. Use only as a physical bus endpoint. GND is the common reference; there is no galvanic isolation, external surge protection or outdoor cable rating. THVD1410DR runs from 3.3 V. GPIO4 TX and GPIO5 RX map to UART1 in future firmware; GPIO10 drives tied DE and /RE, with a 10 kΩ pulldown. Idle defaults to receive.

GPIO3 drives the AO3400A relay transistor through 100 Ω. Both the GPIO and gate have external 10 kΩ pulldowns. G5V-1 DC5 COM uses pins 5 and 6, NO uses pin 10, unused NC is disconnected. Power, boot/reset and relay topology follow Rev B.

The sole RTC is DS3231MZ+, indoors. SDA GPIO0, SCL GPIO1; both have 2.2 kΩ pullups to the switched 3.3 V rail. CR2032 connects directly to VBAT through the keyed cable connector. Assumption: an insulated cabled CR2032 holder is fitted inside the enclosure. No charging circuit is fitted. Use a primary CR2032, not a rechargeable cell. Pins 1, 3 and 4 of the RTC are intentionally disconnected.

## Checks and limits

KiCad 9 schematic and routed PCB are provided with project-local ESP32 footprint and symbols. BOM.csv lists each fitted part and footprint. ERC and DRC reports in checks/ include schematic parity. These checks do not replace independent electrical review, assembly inspection, antenna testing, thermal/current validation or hardware bring-up. No board was fabricated or powered.

THVD1410 pin assignment checked against https://www.ti.com/lit/ds/symlink/thvd1410.pdf .

Final KiCad 9 checks: ERC 0 errors/0 warnings; DRC 0 violations, 0 unconnected pads, 0 schematic parity issues. No exclusions were introduced. Final layout is stable for independent review.
