# Be-In Pod V2 · Rev A

A bench prototype for a QR access reader on one custom controller board. A soldered ESP32-C3-MINI-1-N4X provides the processor, 2.4 GHz Wi-Fi, antenna and 4 MB flash. One RGB LED on the PCB provides status feedback. Omitting an external Linux board and SD card leaves one main PCB to power and mount. Using a radio module keeps the custom board independent of antenna matching and crystal layout. [Espressif module datasheet](https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html)

Rev A uses regulated 5 V bench power. The external scanner decodes QR images and sends data over 3.3 V UART at 9600 baud, 8N1. The board has an optional normally open dry-contact signal relay for a low-voltage controller input. On the bench, use a meter or dummy input to measure the contacts.

## Design files

- [SolidCraft exploded assembly](cad/pod-v2-exploded.sc) shows the populated Rev A board, rear tray, scanner envelope and faceplate as separate solids. Rebuild with `python3 tools/build_exploded.py`. The case and scanner height are estimates for this view. Final fit, scanner retention and cable routing still need measurements.
- [Editable SolidCraft model](cad/pod-v2-rev-a.sc) and [outline STEP](cad/pod-v2-rev-a.step) show the carrier and Wi-Fi module envelope. Rebuild with `python3 tools/build_cad.py` from this directory using SolidCraft 0.48.1. The carrier is 65 × 45 × 1.6 mm with four Ø3.2 mm holes inset 3.5 mm. The module antenna projects 5.4 mm past the board edge. Reserve clearance around it in a housing. [Espressif layout guide](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html)
- [KiCad project](pcb/Pod-A.kicad_pro) and [populated board STEP](pcb/Pod-A.step). Use the KiCad drawings and connector pin assignments in [PCB notes](pcb/README.md) when making the scanner and programming cables. The PCB also opens in SolidCraft 0.48.1.
- [Bench firmware](firmware/) exercises the scanner UART, LED, Wi-Fi, and relay on the workbench. Member access and backend integration require a product firmware port.

## Bench acceptance

1. Check the 3.3 V rail, flash the bench firmware, and check that the contact stays open through power-on, reset, programming, and brownout.
2. Check all three LED colours and Wi-Fi reception. Scan QR codes from a phone while Wi-Fi is active and watch for voltage dips and dropped bytes.
3. Test one deliberate relay pulse into a dummy input. Check that repeated or malformed scanner input leaves the contacts open.

**Assumption for the scanner.** The Waveshare 14810 is a candidate because it has 5 V supply and a documented UART QR protocol. Verify its TX voltage, connector pinout and startup current on the actual module before connecting it, including 3.3 V signal compatibility. [Waveshare 14810](https://www.waveshare.com/catalog/product/view/id/3569/s/barcode-scanner-module/category/37/) · [Scanner command manual](https://files.waveshare.com/upload/d/dd/Barcode_Scanner_Module_Setting_Manual_EN.pdf)
