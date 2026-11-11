from flask import Flask,request,jsonify,render_template,send_file
from datetime import datetime,timezone
from pathlib import Path
import json
from config import UPLOAD_DIR,DEVICE_API_TOKEN
from database import init_db,connection
from services import validate_and_store_image,save_snapshot,process_analysis
app=Flask(__name__);app.config["MAX_CONTENT_LENGTH"]=3*1024*1024
init_db()
def authorized(): return not DEVICE_API_TOKEN or request.headers.get("X-Device-Token","")==DEVICE_API_TOKEN
def number(src,key):
    raw=src.get(key,"")
    if raw is None or str(raw).strip()=="": return None
    try: value=float(raw)
    except (ValueError,TypeError): raise ValueError(f"{key} must be numeric")
    if value!=value or value in (float("inf"),float("-inf")): raise ValueError(f"{key} must be finite")
    return value
def context_from(src):
    device=str(src.get("device_id","plantsense-01"))[:64]
    species=str(src.get("plant_species","unknown"))[:80]
    raw_readings={k:number(src,k) for k in ("temperature_c","humidity_pct","soil_moisture_pct","light_lux")}
    # Missing, disconnected, or invalid sensors are omitted entirely.
    # A genuine measured zero remains a valid reading.
    readings={k:v for k,v in raw_readings.items() if v is not None}
    for k in ("humidity_pct","soil_moisture_pct"):
        if k in readings and not 0<=readings[k]<=100: raise ValueError(f"{k} must be 0..100")
    if "light_lux" in readings and readings["light_lux"]<0: raise ValueError("light_lux cannot be negative")
    if "temperature_c" in readings and not -20<=readings["temperature_c"]<=80: raise ValueError("temperature_c outside accepted range")
    return device,species,readings

@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.get("/api/plant/latest-image")
def latest_image():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con:
        row=con.execute(
            """SELECT p.image_path FROM plant_images p
               WHERE p.device_id=? ORDER BY p.id DESC LIMIT 1""",
            (device,)
        ).fetchone()
    if not row:
        return jsonify({"message":"no image found"}),404
    path=Path(row["image_path"]).resolve()
    # Only serve images stored under the configured upload directory.
    root=UPLOAD_DIR.resolve()
    if root not in path.parents or not path.is_file():
        return jsonify({"error":"image_not_found"}),404
    return send_file(path, mimetype="image/jpeg", conditional=True)

@app.get("/api/health")
def health(): return jsonify({"service":"PlantSense API","status":"ok","timestamp":datetime.now(timezone.utc).isoformat()})
@app.post("/api/plant/analyze")
def analyze():
    if not authorized(): return jsonify({"error":"unauthorized"}),401
    try:
        if "image" not in request.files: return jsonify({"error":"image file required"}),400
        device,species,readings=context_from(request.form)
        pump=request.form.get("pump_state","UNKNOWN")[:10];light=request.form.get("grow_light_state","UNKNOWN")[:10]
        image_path,raw=validate_and_store_image(request.files["image"],device)
        ctx={"device_id":device,"plant_species":species,"growth_stage":request.form.get("growth_stage","unknown")[:80],"sensor_readings":readings,"actuator_state":{"pump":pump,"grow_light":light}}
        outputs,status=process_analysis(raw,ctx)
        result={"plant_species":species,"analysis":outputs,"ai_status":status,"sensor_data":readings,"actuator_state":{"pump":pump,"grow_light":light},"recommendation_is_advisory":True}
        result.update(save_snapshot(device,species,readings,pump,light,image_path,result,status))
        return jsonify(result)
    except ValueError as e: return jsonify({"error":str(e)}),400
    except Exception as e:
        app.logger.exception("Plant analysis failed")
        return jsonify({"error":"analysis_failed","details":str(e)}),502
@app.post("/api/plant/data")
def sensor_data():
    if not authorized(): return jsonify({"error":"unauthorized"}),401
    try:
        payload=request.get_json(force=True);device,species,readings=context_from(payload)
        saved=save_snapshot(device,species,readings,payload.get("pump_state","UNKNOWN"),payload.get("grow_light_state","UNKNOWN"))
        return jsonify({"status":"stored",**saved})
    except (ValueError,TypeError) as e: return jsonify({"error":str(e)}),400
@app.get("/api/plant/latest")
def latest():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con: row=con.execute("SELECT * FROM ai_analysis WHERE device_id=? ORDER BY id DESC LIMIT 1",(device,)).fetchone()
    if not row: return jsonify({"message":"no analysis found"}),404
    return jsonify({"analysis_id":row["id"],"device_id":row["device_id"],"ai_status":row["ai_status"],"created_at":row["created_at"],"result":json.loads(row["result_json"])})
@app.get("/api/plant/history")
def history():
    device=request.args.get("device_id","plantsense-01")
    try: limit=min(max(int(request.args.get("limit",100)),1),500)
    except ValueError: return jsonify({"error":"limit must be integer"}),400
    with connection() as con: rows=con.execute("SELECT * FROM sensor_readings WHERE device_id=? ORDER BY id DESC LIMIT ?",(device,limit)).fetchall()
    # Hide SQL NULL fields from clients; they represent unavailable sensors.
    items=[{k:v for k,v in dict(r).items() if v is not None} for r in rows]
    return jsonify({"device_id":device,"items":items})
if __name__=="__main__":
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    app.run(host="0.0.0.0",port=5000,debug=False)
