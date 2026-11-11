import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")
HF_TOKEN=os.getenv("HF_TOKEN","")
HF_MODEL=os.getenv("HF_MODEL","Qwen/Qwen2.5-VL-3B-Instruct")
ENABLE_HF=os.getenv("ENABLE_HF","true").lower()=="true"
DATABASE_PATH=os.getenv("DATABASE_PATH",str(BASE_DIR/"plantsense.sqlite3"))
UPLOAD_DIR=Path(os.getenv("UPLOAD_DIR",str(BASE_DIR/"uploads")))
DEVICE_API_TOKEN=os.getenv("DEVICE_API_TOKEN","")
MAX_IMAGE_BYTES=2*1024*1024
