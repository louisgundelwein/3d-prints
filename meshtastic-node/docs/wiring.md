# Wiring: candidate, RF switch unverified

**Do not treat this as a complete wiring plan:** the carrier's RF-switch circuit and its compatibility with stock firmware are unverified. The following maps the common signals to the `esp32/diy/v1` firmware; TXEN is provisional. Verify the carrier circuit before applying power or transmitting.

| Signal | Radio pin | ESP32 board label | Colour |
|---|---|---|---|
| Power | VCC | 3V3 | red `#FF0000` |
| Ground | GND | GND (beside 3V3) | black `#000000` |
| SCK | SCK | D5 (GPIO 5) | yellow `#FFFF00` |
| MISO | MISO | D19 (GPIO 19) | green `#008000` |
| MOSI | MOSI | D27 (GPIO 27) | blue `#0000FF` |
| NSS | NSS | D18 (GPIO 18) | orange `#FFA500` |
| Reset | NRST | D23 (GPIO 23) | purple `#800080` |
| DIO1 | DIO1 | D33 (GPIO 33) | white `#FFFFFF` |
| Busy | BUSY | D32 (GPIO 32) | grey `#808080` |
| TX enable (unverified) | TXEN | D13 (GPIO 13) | brown `#A52A2A` |

- VCC goes to 3V3, never VIN. Assumption: use the GND beside 3V3; the closest ground depends on final board placement. Assumption: 100 mm female-to-female wires, adjust after placement.
- RXEN and TXEN are switch controls on the module; the carrier exposes both. Whether this carrier already connects them or requires external drive is unverified. **Do not leave RXEN floating on the assumption that it is internally connected.** The candidate firmware drives TXEN on GPIO 13 but has no RXEN output and disables DIO2 RF switching. A carrier schematic or continuity and switch-circuit verification is needed to decide if stock firmware can operate both directions. DIO2 is not the BUSY signal: firmware's `LORA_DIO2` label maps to radio BUSY.
- The manual says the standard module has a non-temperature-compensated crystal, not a TCXO. The DIY variant has no TCXO voltage defined unless built with `EBYTE_E22` (1.8 V, optional); verify the actual stock build configuration. Crystal operation is expected with 0 V TCXO setting, but actual module and stock binary are unverified.
- Module supply: 1.8–3.7 V, 3.3 V typical; transmit current 100 mA typical, maximum unspecified. Verify the board's 3V3 regulator can supply the ESP32 and radio together.
- All listed GPIOs exist on the stated board, are output-capable and are not flash pins. GPIO 5 is a boot strapping pin; SCK is an input on the radio, so it should not force the boot level, but verify the carrier has no conflicting pull or drive at reset. Other listed GPIOs are not among 0, 2, 5, 12, 15.

## Sources

- Board labels and parts: [README](../README.md).
- Candidate pin definitions: [Meshtastic master `variants/esp32/diy/v1/variant.h`, lines 17–50](https://github.com/meshtastic/firmware/blob/master/variants/esp32/diy/v1/variant.h#L17-L50). DIO2 switch default and pin use: [`src/mesh/SX126xInterface.cpp`, lines 124–157](https://github.com/meshtastic/firmware/blob/master/src/mesh/SX126xInterface.cpp#L124-L157). Master is mutable; the eventual release binary must be checked.
- [DX-LR30 manual](https://ae-pic-a1.aliexpress-media.com/kf/S4f002eea95384325bf342c6686636924r.pdf), PDF pages 6–8 and 10: crystal, voltage, current, pin descriptions. The module manual does not document carrier DX-PJ27-V1.2's connections.

## RXEN wire

The model includes an 11th wire: **RXEN → D14 (GPIO 14), pink `#FF69B4`**, reserved. GPIO 14 is the firmware's RF95_RXEN pin. This way any RF-switch scheme can be used without opening the case to rewire. The firmware step decides how it is used. Assumption: not verified on the carrier.
