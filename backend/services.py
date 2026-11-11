import io,json,uuid
from datetime import datetime,timezone
from PIL import Image,UnidentifiedImageError
from config import UPLOAD_DIR,MAX_IMAGE_BYTES,ENABLE_HF,HF_TOKEN
from database import connection
from hf_client import analyze_with_huggingface
from classifier import predict_with_local_classifier

def utc_now(): return datetime.now(timezone.utc).isoformat()
def validate_and_store_image(upload,device_id):
    raw=upload.read(MAX_IMAGE_BYTES+1)
    if not raw: raise ValueError("Empty image upload")
    if len(raw)>MAX_IMAGE_BYTES: raise ValueError("Image exceeds 2 MB limit")
    try:
        im=Image.open(io.BytesIO(raw)); im.verify()
        if im.format not in ("JPEG","PNG"): raise ValueError("Only JPEG or PNG accepted")
    except (UnidentifiedImageError,OSError): raise ValueError("Invalid image file")
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    safe="".join(c for c in device_id if c.isalnum() or c in "-_")[:40] or "device"
    path=UPLOAD_DIR/f"{safe}_{uuid.uuid4().hex}.jpg"
    with Image.open(io.BytesIO(raw)) as im:
        im=im.convert("RGB");im.thumbnail((1280,1280));im.save(path,"JPEG",quality=88,optimize=True)
    return path,raw

def save_snapshot(device,species,readings,pump,light,image_path=None,result=None,status="not_run"):
    now=utc_now()
    with connection() as con:
        con.execute("INSERT INTO sensor_readings(device_id,plant_species,temperature_c,humidity_pct,soil_moisture_pct,light_lux,pump_state,grow_light_state,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
          (device,species,readings.get("temperature_c"),readings.get("humidity_pct"),readings.get("soil_moisture_pct"),readings.get("light_lux"),pump,light,now))
        image_id=None
        if image_path:
            cur=con.execute("INSERT INTO plant_images(device_id,image_path,created_at) VALUES(?,?,?)",(device,str(image_path),now));image_id=cur.lastrowid
        analysis_id=None
        if result is not None:
            cur=con.execute("INSERT INTO ai_analysis(image_id,device_id,result_json,ai_status,created_at) VALUES(?,?,?,?,?)",(image_id,device,json.dumps(result),status,now));analysis_id=cur.lastrowid
    return {"image_id":image_id,"analysis_id":analysis_id,"timestamp":now}

def process_analysis(image_bytes,context):
    outputs={};status="not_configured"
    if ENABLE_HF and HF_TOKEN:
        outputs["vlm"]=analyze_with_huggingface(image_bytes,context);status="completed"
    else: outputs["vlm"]={"status":"not_configured","message":"Set HF_TOKEN and ENABLE_HF=true"}
    outputs["classifier"]=predict_with_local_classifier(image_bytes)
    return outputs,status
