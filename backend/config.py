import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Groq vision-language inference
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()
ENABLE_GROQ = os.getenv("ENABLE_GROQ", "true").lower() == "true"

# Retained temporarily for compatibility with the earlier Hugging Face setup.
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "")
ENABLE_HF = os.getenv("ENABLE_HF", "false").lower() == "true"

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "plantsense.sqlite3"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
DEVICE_API_TOKEN = os.getenv("DEVICE_API_TOKEN", "")
MAX_IMAGE_BYTES = 2 * 1024 * 1024
