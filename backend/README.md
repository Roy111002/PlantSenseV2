# Backend
Install `requirements.txt`, copy `.env.example` to `.env`, set HF_TOKEN, then run `python app.py`.
Check `/api/health`. To test image upload:
```bash
curl -X POST http://127.0.0.1:5000/api/plant/analyze -F "image=@sample.jpg" -F "device_id=plantsense-01" -F "plant_species=tomato" -F "temperature_c=28" -F "humidity_pct=65" -F "soil_moisture_pct=42" -F "light_lux=4500"
```
The firmware sends the optional X-Device-Token header on both image and telemetry uploads. Match firmware DEVICE_API_TOKEN to the backend value when enabling authentication.


## Missing sensor readings

Leave an unavailable sensor's multipart field blank. The API omits that measurement
from AI context and JSON responses. Genuine zero values remain valid measurements.
