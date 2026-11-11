# PlantSense dashboard – incremental integration

Copy the following new files into the existing repository, preserving paths:

- `backend/templates/dashboard.html`
- `backend/static/css/dashboard.css`
- `backend/static/js/dashboard.js`

Then apply `backend/app.py.patch` from the repository root:

```bash
git apply backend/app.py.patch
```

The patch adds Flask template/static imports, `/dashboard`, `/api/plant/latest-image`, and includes actuator state in the latest analysis JSON. No firmware files or requirements changes are needed.

Run from `backend/`:

```bash
python app.py
```

Open `http://127.0.0.1:5000/dashboard`.

The dashboard polls every 10 seconds. Set the device ID field to the same ID sent by the ESP32. It hides absent sensor values, preserves real zero values, marks readings older than two minutes as stale, and does not send actuator commands.

If your repository's `app.py` has diverged, do not force-apply the patch. Open `app.py.patch` and make the equivalent additions manually, or share the current file for a tailored patch.
