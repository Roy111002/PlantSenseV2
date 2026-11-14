# PlantSense Groq integration

## Files to copy into the existing repository

Copy the contents of this package into your repository root, preserving paths.
It adds `backend/groq_client.py` and replaces `backend/config.py`,
`backend/services.py`, and `backend/.env.example`.

## Configure the API key

Create a key at https://console.groq.com/keys. In `backend/.env`, set:

```env
GROQ_API_KEY=gsk_your_real_key
GROQ_MODEL=qwen/qwen3.8-27b
ENABLE_GROQ=true
ENABLE_HF=false
```

Keep the rest of your existing `.env` values (`DATABASE_PATH`, `UPLOAD_DIR`,
and `DEVICE_API_TOKEN`) unchanged. Do not commit `.env`.

## Dependencies

No new Python package is required: this project already installs `openai`,
and Groq exposes an OpenAI-compatible chat-completions endpoint.

If your installed OpenAI package is old, update it:

```powershell
python -m pip install --upgrade openai
```

## Restart and test

From `backend`:

```powershell
python app.py
```

In a second PowerShell window, test with a local image:

```powershell
curl.exe -X POST "http://127.0.0.1:5000/api/plant/analyze" `
  -F "image=@D:\PlantSense-AI-v2\test-images\plant.jpg" `
  -F "device_id=plantsense-01" `
  -F "plant_species=Tomato" `
  -F "growth_stage=Vegetative"
```

The response keeps the existing shape: `analysis.vlm`, `analysis.classifier`,
`sensor_data`, `ai_status`, and database IDs. The VLM result uses the same
diagnosis keys expected by the dashboard.

## Notes

- The configured model ID is `qwen/qwen3.8-27b`, which Groq documents as a
  vision-capable model with JSON mode.
- Groq's model pricing and organization rate limits are account-dependent.
  Check your Groq console before assuming requests are free.
- The application does not run AI analysis on ordinary sensor telemetry
  requests; image analysis happens through `/api/plant/analyze`.
