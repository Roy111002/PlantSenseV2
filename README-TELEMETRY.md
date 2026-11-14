# Sensor telemetry and actuator reporting

The ESP32 sends JSON telemetry to `/api/plant/data` approximately every five
seconds while Wi-Fi is connected. It samples sensors every five seconds and
reports temperature (C), humidity (%), calibrated soil moisture (%), light (lux),
and pump/grow-light GPIO output states. Failed requests retry on the next interval;
there is no offline backlog. Image uploads remain separate, approximately every
five minutes, and retain the Groq analysis integration.

Telemetry and image HTTP requests run in separate FreeRTOS tasks. The main loop
keeps updating local automation while either request is waiting. The pump runtime
limit is checked each loop, and an unavailable soil reading stops the pump.
An unavailable light reading turns the grow light off.

## Hardware configuration

`esp32_firmware/config.h` now reflects the supplied AI-Thinker wiring:

| Signal | GPIO / connection |
| --- | --- |
| DHT22 DATA | GPIO2 (IO2; confirm this is not header position 2) |
| BH1750 and ADS1115 SDA | GPIO13 |
| BH1750 and ADS1115 SCL | GPIO14 |
| Soil sensor AO | ADS1115 A0 (A-zero), confirmed |
| ADS1115 ADDR | GND, address 0x48 |
| BH1750 address | Default 0x23; ADDR left unconnected, verify detection |
| Pump / grow light | Not connected; GPIOs remain -1 |

MicroSD and onboard flash LED are unused. The camera keeps the AI-Thinker pin
map; the reported RHYXM21-45 marking alone does not confirm its sensor model.
Programming/power connection: laptop USB -> FT232RL -> ESP32-CAM, with GND to
GND, VCC to VCC, RX to TX, and TX to RX. The user reports the FT232RL jumper is
set to 3.3 V. Actual VCC/UART levels and the module's available power current
are not yet measured; jumper behavior depends on the breakout circuit.
If VCC is supplied by the FT232RL chip's 3V3OUT, its 50 mA limit is insufficient:
Espressif specifies at least 500 mA supply capability for the ESP32 alone.
Use an adequately rated board supply and keep UART logic at 3.3 V; identify the
ESP32-CAM input pin before changing any supply voltage. Disconnect the FTDI VCC
lead when using a separate supply, and retain the common ground and crossed UART.
References: [FT232R datasheet](https://ftdichip.com/wp-content/uploads/2020/08/DS_FT232R.pdf),
[ESP32 power requirements](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/schematic-checklist.html).
Power rail verification, DHT pull-up/module details, and soil calibration are pending.
Do not treat a pin labelled VCC as confirmed 3.3 V. ESP32 data signals and I2C
pull-ups must stay within the board's 3.3 V logic limits. Verify the exact sensor
module power requirements before powering the circuit.

GPIO2 must be low or floating to enter the serial bootloader. A DHT DATA pull-up
can interfere with flashing; if it does, disconnect DATA from IO2 for flashing
and reconnect it after upload, with power off while changing wiring.
Reference: [Espressif boot mode documentation](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html).

Still to configure:

- Wi-Fi credentials are saved locally in ignored `esp32_firmware/wifi_secrets.h`.
  For a new checkout, copy `wifi_secrets.example.h` to `wifi_secrets.h` and fill it.
  Do not share the local secrets header or firmware binaries containing it.
- Both API URLs use the supplied PC LAN address `192.168.0.103`, port 5000.
  Update both in `config.h` if the PC's IP changes.
- Set `DEVICE_ID`, `PLANT_SPECIES`, and `GROWTH_STAGE`.
- GPIO2 and ADS1115 A0 are confirmed. BH1750 ADDR is unused; verify detection
  at 0x23 during startup. If ADDR is later connected HIGH, change the address to 0x5C.
- Leave pump and grow-light pins at `-1` until those devices and drivers are added.
- Calibrate `SOIL_ADC_DRY` / `SOIL_ADC_WET` and review the species thresholds.
  Serial Monitor at 115200 baud now prints `[SOIL] ... raw=...` for calibration.
- If backend `DEVICE_API_TOKEN` is enabled, put its matching value in firmware
  `DEVICE_API_TOKEN`. Both upload types send `X-Device-Token`.

The existing driver convention is **active HIGH**. Confirm the driver polarity
before assigning pins. Reported `ON` / `OFF` comes from GPIO readback; it does not
confirm water flow or emitted light. Unconfigured outputs report `UNKNOWN`.

Unavailable sensor readings are omitted, stored as SQL NULL, and hidden by the
dashboard. Real zero values are retained. ADS1115 communication loss can be
detected, but an unplugged analog probe on a connected ADS1115 may float and
cannot reliably be detected by software alone. Failed sensor initialization is
retried on device restart.

## API and dashboard

- `POST /api/plant/data`: stores telemetry without calling Groq.
- `GET /api/plant/latest-data?device_id=plantsense-01`: latest telemetry with
  `sensor_data`, `actuator_state` (`pump`, `grow_light`), and `created_at` in UTC.
- `GET /api/plant/history?device_id=plantsense-01&limit=50`: latest readings,
  ordered by receipt time. Missing measurements are omitted.
- `/api/plant/latest` continues returning the latest AI analysis and its original
  image-associated sensor context.

The dashboard polls every ten seconds and uses `/latest-data` for its current
sensor cards and actuator states. Image/AI panels remain independent. Values
older than two minutes are marked stale. A slow image analysis does not replace
newer telemetry. No database migration is needed.

## Simulate telemetry in PowerShell

Start the backend in one terminal:

```powershell
Set-Location D:\PlantSense-AI-v2\backend
python app.py
```

In another terminal:

```powershell
Set-Location D:\PlantSense-AI-v2
.\backend\test-telemetry.ps1
# If token authentication is enabled, add -DeviceToken with the matching value.
```

The script stores sample readings under `plantsense-simulated`, with pump `OFF`
and grow light `ON`. Select that device at `http://127.0.0.1:5000/dashboard`.
It reports simulated states only and sends no actuator commands or AI requests.

## Local regression checks

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m unittest discover -s backend/tests -v
node backend/tests/dashboard_telemetry.test.js
```

API tests use a temporary database and mocked AI. GPIO simulation uses `g++`
when available to check pump deadlines, cooldown, sensor failures, and states.

For Arduino CLI, the sketch folder must match `PlantSense.ino`. Stage a build
copy (the original firmware files remain under `esp32_firmware`):

```powershell
New-Item -ItemType Directory -Force .build/PlantSense | Out-Null
Copy-Item esp32_firmware/* .build/PlantSense/
arduino-cli compile --fqbn esp32:esp32:esp32cam .build/PlantSense
```

Use the libraries listed in the main README. For Arduino IDE, open the staged
`.build/PlantSense/PlantSense.ino`. Always restage after editing the source.
Hardware flashing and physical end-to-end verification remain pending wiring.
