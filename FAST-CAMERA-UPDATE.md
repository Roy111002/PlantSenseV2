# Fresh camera snapshots

The camera now discards frames captured before the current capture request and
rejects frames older than two seconds at acquisition. It captures immediately
after Wi-Fi connects, then targets a fresh upload every five seconds. Failed
uploads are discarded and the next attempt captures a new scene. The retry
interval is two seconds, in addition to time spent on the failed request.
There is no offline image backlog. Local actuator control stays independent.

The firmware derives `/api/plant/snapshot` from the configured `/api/plant/analyze`
URL, so existing laptop IP settings are retained. Update backend and firmware
together. Snapshot requests return 201 for image-only storage or 202 when AI is
queued. The original synchronous `/api/plant/analyze` endpoint remains available.

Images become visible as soon as they are validated and stored. Groq runs in a
separate worker; failure there leaves the image visible. AI is requested on the
first accepted image and every five minutes thereafter. Only the latest waiting
AI job per device is kept. Queued work survives backend restart. The worker is
intended for the existing single-process `python app.py` deployment.

The dashboard polls every two seconds, downloads images only when their ID
changes, and guards against older downloads replacing newer frames. The image
panel shows receipt time and labels previews older than 15 seconds as stale.
AI observations show which image they belong to. AI results may arrive later
than the current preview. SQLite uses WAL and indexes for concurrent access.

This is a frequently updated snapshot preview, not a video stream. On a healthy
LAN, new scenes should appear within roughly one capture interval plus transfer
and polling time. Hardware/network connection failures can still add delay;
these software changes cannot guarantee uninterrupted connectivity. Frequent
snapshots are retained in the configured upload storage, so disk usage increases.

## Install on the laptop running the cloned project

Stop Flask with Ctrl+C. Extract `fast-camera-update.zip`, open PowerShell in the
extracted folder, then run:

```powershell
.\tools\install-fast-camera-update.ps1 -ProjectRoot 'C:\Users\User\PlantSenseV2'
```

The installer backs up replaced source files under `.update-backups`, updates
the required source, and changes only timing constants in your firmware config.
It preserves your current backend IP, Wi-Fi header, GPIO settings, `.env`,
database, and uploads. The package contains no credentials or saved images.
It replaces the listed source files; backups preserve any laptop-only edits.

Restart the backend in one terminal:

```powershell
Set-Location C:\Users\User\PlantSenseV2\backend
python app.py
```

Restage the sketch in another terminal:

```powershell
Set-Location C:\Users\User\PlantSenseV2
New-Item -ItemType Directory -Force .build/PlantSense | Out-Null
Copy-Item esp32_firmware/* .build/PlantSense/ -Force
```

Open `.build/PlantSense/PlantSense.ino` in Arduino IDE and upload using the MB
board's COM port. Hard-refresh the dashboard with Ctrl+F5. No new Python package
is needed. The existing SQLite database is upgraded automatically at startup.

## Verify freshness

Change the scene visibly (for example, move a labelled object into view). Check
the serial `[CAMERA] fresh frame ... age=... ms` and `[API] HTTP 201/202` logs.
The preview should update without waiting for AI. Compare its image ID and
receipt time with `/api/plant/latest-image-info?device_id=plantsense-01`.
Check that AI may show queued/processing and later completed for its own image
ID while previews continue updating. No physical camera or router is available
in the development environment; confirm the final timing on the actual hardware.
