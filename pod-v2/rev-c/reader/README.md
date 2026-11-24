# Rev C outdoor reader

The 72 × 100 mm reader retains the Rev B scanner opening, mounting holes, front LED ring and NFC antenna clearance. Open [Pod-C-Reader.kicad_pro](Pod-C-Reader.kicad_pro) in KiCad 9. See [Rev B scanner and NFC assembly](../../rev-b/pcb/README.md#assembly-and-cables) for the optical engine, flex and keyed module harness.

| Connector | Contacts |
| --- | --- |
| J1 bench power | 1 regulated 5 V, 2 GND |
| J2 scanner flex | 2 3.3 V, 3 GND, 4 host TX, 5 engine TX, 12 active-low trigger. Other contacts open. |
| J3 RS-485 | 1 A (noninverting), 2 B (inverting), 3 signal GND. 120 Ω across A/B on the board. |
| J4 programming UART | 1 GND, 2 host TX, 3 host RX. Use 3.3 V serial levels. |
| J5 NFC | 1 open, 2 SDA, 3 SCL, 4 IRQ, 5 VEN, 6 3.3 V, 7 GND, 8 5 V |

| Function | ESP32-C3 GPIO |
| --- | --- |
| Bus UART0 TX / RX / direction | 18 / 19 / 3 |
| UART0 ROM programming TX / RX | 21 / 20 |
| Scanner UART1 TX / RX | 4 / 5 |
| NFC SDA / SCL / IRQ / VEN | 0 / 1 / 6 / 7 |
| RGB pixel data | 10 |

Remap UART0 to GPIO18/19 in application firmware and disable the UART0 application console so log bytes stay off the bus. GPIO18/19 are the native USB pins. Use J4 for ROM download. GPIO3 is pulled low at reset, enabling receiver mode with the transmitter disabled. [ESP32-C3 module](https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html) · [THVD1410](https://www.ti.com/product/THVD1410)

Start at 5.0 V measured at J1 with a regulated current-limited bench supply. Check that the TRACO input and NFC VANT remain at least 4.75 V at full combined load and measure scanner supply ripple (50 mV peak-to-peak maximum). This board is for a controlled, short, common-ground bus. The actual run needs cable, grounding and surge validation. [TRACO TSR 1](https://www.tracopower.com/products/tsr1.pdf) · [ELECHOUSE](https://www.elechouse.com/docs/pn7160/) · [Newland integration guide](https://newlandemea.katanapim.com/AttachmentDownload/Download/688?name=EM3080-W+V2_Integration+Guide_V1+2026.pdf)
