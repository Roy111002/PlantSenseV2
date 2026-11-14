# PlantSense AI Pod — starter implementation

This starter contains AI-Thinker ESP32-CAM firmware, a Flask backend, Hugging Face VLM integration, SQLite storage, and dataset/training scaffolds.

## Architecture
1. ESP32-CAM reads sensors and runs pump/light rules locally.
2. It periodically uploads JPEG + sensor readings to Flask.
3. Flask stores the image/telemetry and calls a Hugging Face vision-language model.
4. An optional local classifier hook is provided for the later trained model.

## Hardware safety
- Sensor GPIOs follow the supplied wiring: DHT22 on GPIO2, shared I2C SDA/SCL on GPIO13/14. Pump/light GPIOs remain `-1` and disabled. Verify power rails and remaining wiring details in README-TELEMETRY.md before hardware testing.
- Camera pins are the AI-Thinker pin map and must not be reused.
- ESP32-CAM has constrained GPIO availability and boot-strapping pin caveats. Finalize pin mapping only after seeing your exact board and circuit.
- Never power a pump or bulb from a GPIO. Use a correctly rated logic-level MOSFET driver and separate regulated load supply. DC pump needs suitable flyback protection.
- Never connect a 230V household LED bulb to this breadboard/MOSFET circuit. Demonstrate with a low-voltage DC LED module.
- Pump runtime/cooldown protection is included, but test with pump disconnected first.
- Thresholds are examples only; multiple species need calibrated profiles.

## ESP32 setup
Open `esp32_firmware/PlantSense.ino` in Arduino IDE. Install ESP32 board support and libraries: DHT sensor library (Adafruit), Adafruit Unified Sensor, BH1750, Adafruit ADS1X15, ArduinoJson. Select AI Thinker ESP32-CAM and enable PSRAM if present. Edit `config.h` with Wi-Fi, backend URL, species, and eventually GPIOs/calibration.

## Backend setup
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
# Edit .env and set HF_TOKEN
python app.py
```
Test `http://127.0.0.1:5000/api/health`. For ESP32, use your PC LAN IP in `API_ANALYZE_URL`, not localhost. Keep both devices on the same LAN and allow TCP 5000 through your firewall.

## API
- `GET /api/plant/latest-data?device_id=plantsense-01` for current telemetry and actuator states
- `GET /api/health`
- `POST /api/plant/analyze` multipart: image, device_id, plant_species, growth_stage, temperature_c, humidity_pct, soil_moisture_pct, light_lux, pump_state, grow_light_state
- `POST /api/plant/data` JSON telemetry
- `GET /api/plant/latest?device_id=plantsense-01`
- `GET /api/plant/history?device_id=plantsense-01&limit=100`

Sensor telemetry and GPIO state reporting are implemented separately from image
analysis. See [telemetry setup and simulation](README-TELEMETRY.md) for the current
configuration, dashboard behavior, PowerShell test, and hardware placeholders.

For cloud deployment use HTTPS, a production WSGI server, authentication, firewall rules, and persistent storage. Do not expose Flask development server publicly.

## Multi-species + AI plan
Send the actual species in each upload. VLM receives species and sensor context. The local classifier adapter is inactive until a trained model is installed. Dataset README explains metadata and leakage-safe splits. VLM outputs are screening suggestions, not confirmed diagnoses.


## Missing / disconnected sensor handling

The ESP32 firmware marks a sensor reading as valid only when its module is initialized
and returns a valid measurement. Invalid/unavailable readings are uploaded as empty
fields. The Flask backend omits those fields from the AI context and API response.
SQLite stores corresponding nullable columns as SQL NULL, and the history endpoint
filters those NULL fields so they do not appear to dashboard clients.

A real measured zero is retained (for example, 0 lux at night); zero is never used as
a disconnected-sensor marker.
