"""Verify cross-laptop installation preserves local credentials and addresses."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("powershell"),"PowerShell is required for the update installer")
class InstallerTests(unittest.TestCase):
    def test_install_preserves_configuration_and_backs_up_source(self):
        repository=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)
            (target/"backend").mkdir()
            (target/"esp32_firmware").mkdir()
            (target/"backend/app.py").write_text("# previous app\n")
            (target/"backend/.env").write_text("LOCAL_SETTING=keep-me\n")
            (target/"backend/plantsense.sqlite3").write_bytes(b"existing-database")
            (target/"esp32_firmware/PlantSense.ino").write_text("// previous firmware\n")
            (target/"esp32_firmware/wifi_secrets.h").write_text("// keep local credentials\n")
            config='''#pragma once
static const char* API_ANALYZE_URL="http://192.168.0.101:5000/api/plant/analyze";
static constexpr int PIN_DHT=2;
static constexpr uint32_t IMAGE_INTERVAL_MS=300000;
static constexpr uint32_t HTTP_TIMEOUT_MS=60000;
'''
            (target/"esp32_firmware/config.h").write_text(config)
            subprocess.run([shutil.which("powershell"),"-NoProfile","-File",
                            str(repository/"tools/install-fast-camera-update.ps1"),
                            "-ProjectRoot",str(target)],check=True,capture_output=True,text=True,timeout=20)
            installed=(target/"esp32_firmware/config.h").read_text()
            self.assertIn('API_ANALYZE_URL="http://192.168.0.101:5000/api/plant/analyze"',installed)
            self.assertIn("PIN_DHT=2",installed)
            self.assertIn("IMAGE_INTERVAL_MS = 5000;",installed)
            self.assertIn("AI_INTERVAL_MS = 300000;",installed)
            self.assertIn("uint16_t HTTP_TIMEOUT_MS = 10000;",installed)
            self.assertEqual((target/"backend/.env").read_text(),"LOCAL_SETTING=keep-me\n")
            self.assertEqual((target/"esp32_firmware/wifi_secrets.h").read_text(),"// keep local credentials\n")
            self.assertEqual((target/"backend/plantsense.sqlite3").read_bytes(),b"existing-database")
            backups=list((target/".update-backups").glob("*/backend/app.py"))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_text(),"# previous app\n")
            self.assertTrue((target/"backend/analysis_worker.py").is_file())
