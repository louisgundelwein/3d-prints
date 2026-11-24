# Be-In Pod Rev C

Rev C is a two-board bench prototype. The outdoor reader keeps the ESP32-C3, Newland QR engine, PN7160 module and 12-pixel ring from Rev B. The protected indoor controller owns the door contact and the battery-backed clock.

| Board | Function | Files |
| --- | --- | --- |
| Outdoor reader | Collect QR and NFC evidence and display the controller's decision | [KiCad project](reader/Pod-C-Reader.kicad_pro) · [BOM](reader/BOM.csv) · [Wiring](reader/README.md) |
| Indoor controller | Decide access and operate the normally open dry contact | [KiCad project](indoor/Indoor.kicad_pro) · [Wiring](indoor/README.md) |

## Bench connection

Connect reader J3 to indoor J2 by signal name: A to A, B to B, and GND to GND. Use a 120 Ω twisted pair for A/B and a signal ground conductor. Each board terminates one end with 120 Ω. The two boards have separate regulated 5 V inputs. Start with short wiring and controlled common ground. Fit a non-rechargeable CR2032 in a secured, replaceable holder near the indoor board. Check the holder wiring against the indoor battery header before plugging it in. The battery powers only the clock.

**Assumption:** The installed controller exposes a low-voltage dry-contact input. Validate the site voltage, contact load, pulse duration, cable grounding and surge exposure before selecting an installation configuration. Use a meter or a dummy controller input on the bench.

## Firmware contract

The indoor controller must authenticate the reader and independently validate the presented credential or a backend authorization. Bind the authorization to the intended door and a fresh transaction. Reject invalid or repeated transactions and bound relay activation time. Cable loss, restart and an untrusted clock must leave the contact open. An authenticated reader message by itself is insufficient to grant access.

Initialize the clock from a trusted time source and verify the write before clearing its oscillator-stop flag. Keep the oscillator enabled in battery mode and disable the unused 32 kHz output. On boot, use the clock for time-limited credentials only if its status and time are valid. Persist the check-in before the pulse and use its unique ID to deduplicate upload after reconnection. [DS3231M datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/DS3231M.pdf)

Rev C does not include that firmware. The existing Rev A bench commands do not apply to Rev C. The reader's QR and NFC interfaces and the indoor controller's UART and GPIO assignments are documented with their boards.

## First hardware check

1. Verify battery polarity, then set a known clock time. Disconnect main power and network, restore power, and compare elapsed time. Repeat with the battery removed and confirm the clock reports invalid time after losing both supplies.
2. On the unpowered paired bus, measure about 60 Ω between A and B. Power both boards and verify communication under simultaneous QR, NFC, LED and Wi-Fi load. Check the rails and scanner ripple.
3. Use a dummy input to confirm the contact stays open through startup, brownout, cable loss, malformed messages and firmware resets. With firmware implemented, accept a valid signed test credential once, reject an expired one after an offline reboot, and verify check-in upload deduplicates.

Reader and indoor mounting, installation power and cable behavior remain to be validated on hardware.
