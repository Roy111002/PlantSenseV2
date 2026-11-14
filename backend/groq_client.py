import base64
import json
from io import BytesIO

from openai import OpenAI
from PIL import Image

from config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """You are PlantSense, a cautious plant-health screening assistant.
Analyze the supplied plant photograph together with the plant species, growth
stage, and available sensor readings.

Do not claim a definitive diagnosis from one photograph. Distinguish visible
evidence from possible causes. If the image is unclear or evidence is
insufficient, use an uncertain assessment. Do not invent sensor readings.

Return one valid JSON object with exactly these keys:
{
  "plant_condition": "healthy|possible_stress|possible_disease|uncertain",
  "disease": "string or null",
  "stress_level": "none|low|medium|high|uncertain",
  "visible_symptoms": ["..."],
  "possible_causes": ["..."],
  "confidence": 0.0,
  "recommendation": "string",
  "limitations": ["..."]
}
Confidence must be a number from 0 to 1 and is a subjective estimate, not
a calibrated probability. Use null for disease when no disease is identified.
Return JSON only, without Markdown fences.
"""


def analyze_with_groq(image_bytes, context):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured in backend/.env")

    # Normalize JPEG/PNG uploads to JPEG so the data URL always matches bytes.
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGB")
            image.thumbnail((1280, 1280))
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=88, optimize=True)
            jpeg_bytes = buffer.getvalue()
    except Exception as exc:
        raise ValueError(f"Could not prepare image for Groq: {exc}") from exc

    data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
        timeout=90.0,
        max_retries=1,
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this plant image. Plant context and available "
                            "measurements follow. Missing sensor readings are absent "
                            "and must not be assumed:\n"
                            + json.dumps(context, ensure_ascii=False)
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        temperature=0.2,
        max_tokens=900,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or ""
    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    content = content.strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        return {
            "plant_condition": "uncertain",
            "raw_model_response": content,
            "parse_error": "Groq returned content that was not valid JSON",
        }

    # Keep a predictable shape for the dashboard and future classifier.
    result.setdefault("plant_condition", "uncertain")
    result.setdefault("disease", None)
    result.setdefault("stress_level", "uncertain")
    result.setdefault("visible_symptoms", [])
    result.setdefault("possible_causes", [])
    result.setdefault("confidence", None)
    result.setdefault("recommendation", "")
    result.setdefault("limitations", [])
    return result
