# Pod V2 bench firmware

Build for the ESP32-C3-MINI-1-N4X with ESP-IDF v5.4.2. From this directory run:

```sh
docker run --rm -v "$PWD:/project" -w /project espressif/idf:v5.4.2 idf.py build
```

Power the board externally. Connect a 3.3 V USB-to-UART adapter to the UART0 programming/debug header: adapter TX to board RX, adapter RX to board TX, and GND to GND. Leave adapter power disconnected. Open the adapter's serial port at 115200 baud, 8N1, no flow control. Send each command on its own line.

| Command | Bench check |
| --- | --- |
| `red`, `green`, `blue`, `off` | Select one common-cathode LED channel or turn all off (GPIO0/1/10). |
| `scanner` | Read the cumulative UART1 byte count. Compare before and after a scan. MCU RX is GPIO5, TX is GPIO4, 9600 baud, 8N1. |
| `wifi` | Count visible access points with a passive scan. |
| `pulse relay` | Drive GPIO3 high for four seconds, then low. Check with an unloaded relay. |

GPIO3 requires the board's external pulldown to keep the relay off during reset. Scanner bytes are counted and discarded.
