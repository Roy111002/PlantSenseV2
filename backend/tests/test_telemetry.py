"""Isolated API regression checks. No production DB, credentials, or AI requests."""
import io
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.temp.name) / "test.sqlite3")
        cls.env = patch.dict(os.environ, {
            "DATABASE_PATH": cls.db_path,
            "UPLOAD_DIR": str(Path(cls.temp.name) / "uploads"),
            "DEVICE_API_TOKEN": "test-device-token",
            "ENABLE_GROQ": "false",
            "GROQ_API_KEY": "",
        })
        cls.env.start()
        import app
        cls.api = app
        cls.client = app.app.test_client()
        cls.headers = {"X-Device-Token": "test-device-token"}

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.temp.cleanup()

    def post(self, payload, **kwargs):
        return self.client.post("/api/plant/data", json=payload,
                                headers=self.headers, **kwargs)

    def test_full_telemetry_without_ai(self):
        payload = dict(device_id="full", plant_species="Tomato",
                       temperature_c=28, humidity_pct=65,
                       soil_moisture_pct=42, light_lux=4500,
                       pump_state="on", grow_light_state="off")
        with patch.object(self.api, "process_analysis", side_effect=AssertionError("AI called")):
            self.assertEqual(self.post(payload).status_code, 200)
        latest = self.client.get("/api/plant/latest-data?device_id=full").get_json()
        self.assertEqual(latest["sensor_data"]["soil_moisture_pct"], 42)
        self.assertEqual(len(latest["sensor_data"]), 4)
        self.assertEqual(latest["actuator_state"], {"pump": "ON", "grow_light": "OFF"})
        self.assertTrue(latest["created_at"].endswith("+00:00"))
        self.assertEqual(self.client.get("/api/plant/latest?device_id=full").status_code, 404)

    def test_disconnected_sensors_replace_previous_values_and_keep_zero(self):
        self.post(dict(device_id="missing", temperature_c=28, light_lux=100))
        self.post(dict(device_id="missing", temperature_c=None,
                       humidity_pct="", light_lux=0))
        data = self.client.get("/api/plant/latest-data?device_id=missing").get_json()
        self.assertEqual(data["sensor_data"], {"light_lux": 0})
        self.assertEqual(data["actuator_state"], {"pump": "UNKNOWN", "grow_light": "UNKNOWN"})
        row = self.client.get("/api/plant/history?device_id=missing").get_json()["items"][0]
        self.assertNotIn("temperature_c", row)
        self.assertEqual(row["light_lux"], 0)
        with closing(sqlite3.connect(self.db_path)) as con:
            self.assertIsNone(con.execute("SELECT temperature_c FROM sensor_readings WHERE device_id='missing' ORDER BY id DESC LIMIT 1").fetchone()[0])

    def test_bad_readings_and_states_rejected(self):
        for fields in ({"humidity_pct": 101}, {"soil_moisture_pct": -1},
                       {"light_lux": -1}, {"temperature_c": "nan"},
                       {"pump_state": "broken"}, {"grow_light_state": True}):
            with self.subTest(fields=fields):
                self.assertEqual(self.post(dict(device_id="bad", **fields)).status_code, 400)
        for payload in ([], "bad", 1):
            self.assertEqual(self.post(payload).status_code, 400)

    def test_authentication(self):
        for headers in ({}, {"X-Device-Token": "wrong"}):
            response = self.client.post("/api/plant/data", json={}, headers=headers)
            self.assertEqual(response.status_code, 401)

    def test_unknown_device_isolated(self):
        self.assertEqual(self.client.get("/api/plant/latest-data?device_id=absent").status_code, 404)

    @unittest.skipUnless(shutil.which("powershell"), "PowerShell is required for the simulation script")
    def test_powershell_simulation_over_http(self):
        from werkzeug.serving import make_server
        server = make_server("127.0.0.1", 0, self.api.app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            script = Path(__file__).resolve().parents[1] / "test-telemetry.ps1"
            result = subprocess.run([
                shutil.which("powershell"), "-NoProfile", "-File", str(script),
                "-BaseUrl", f"http://127.0.0.1:{server.server_port}",
                "-DeviceId", "powershell-simulated", "-DeviceToken", "test-device-token",
            ], check=True, capture_output=True, text=True, timeout=20)
            self.assertIn("powershell-simulated", result.stdout)
            latest = self.client.get("/api/plant/latest-data?device_id=powershell-simulated").get_json()
            self.assertEqual(latest["sensor_data"]["temperature_c"], 28)
            self.assertEqual(latest["actuator_state"], {"pump": "OFF", "grow_light": "ON"})
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_slow_image_analysis_does_not_replace_newer_telemetry(self):
        from PIL import Image
        image = io.BytesIO()
        Image.new("RGB", (8, 8), "green").save(image, "JPEG")
        image.seek(0)

        def slow_analysis(raw, context):
            # A new telemetry request arrives while the older image is being analyzed.
            self.post(dict(device_id="overlap", temperature_c=30,
                           pump_state="OFF", grow_light_state="ON"))
            return {"vlm": {"plant_condition": "healthy"}}, "completed"

        with patch.object(self.api, "process_analysis", side_effect=slow_analysis):
            response = self.client.post("/api/plant/analyze", headers=self.headers, data={
                "image": (image, "plant.jpg"), "device_id": "overlap",
                "temperature_c": "20", "pump_state": "ON", "grow_light_state": "OFF",
            })
        self.assertEqual(response.status_code, 200)
        latest = self.client.get("/api/plant/latest-data?device_id=overlap").get_json()
        self.assertEqual(latest["sensor_data"], {"temperature_c": 30})
        self.assertEqual(latest["actuator_state"]["pump"], "OFF")
        analysis = self.client.get("/api/plant/latest?device_id=overlap").get_json()
        self.assertEqual(analysis["result"]["sensor_data"]["temperature_c"], 20)
        with self.client.get("/api/plant/latest-image?device_id=overlap") as image_response:
            self.assertEqual(image_response.status_code, 200)
        history = self.client.get("/api/plant/history?device_id=overlap").get_json()["items"]
        self.assertEqual([row["temperature_c"] for row in history], [30, 20])


if __name__ == "__main__":
    unittest.main()
