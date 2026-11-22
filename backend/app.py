from flask import Flask,request,jsonify,render_template,send_file
from datetime import datetime,timezone
from pathlib import Path
import json
from config import UPLOAD_DIR,DEVICE_API_TOKEN
from database import init_db,connection
from services import validate_and_store_image,save_snapshot,process_analysis,utc_now
from analysis_worker import start_analysis_worker
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
    if not hasattr(src,"get"): raise ValueError("payload must be a JSON object")
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

def actuator_states(src):
    states=[]
    for key in ("pump_state","grow_light_state"):
        value=src.get(key,"UNKNOWN")
        value="UNKNOWN" if value is None else str(value).strip().upper()
        if value not in ("ON","OFF","UNKNOWN"):
            raise ValueError(f"{key} must be ON, OFF, or UNKNOWN")
        states.append(value)
    return states

def telemetry_from_row(row):
    keys=("temperature_c","humidity_pct","soil_moisture_pct","light_lux")
    return {"reading_id":row["id"],"device_id":row["device_id"],
            "plant_species":row["plant_species"],"created_at":row["created_at"],
            "sensor_data":{k:row[k] for k in keys if row[k] is not None},
            "actuator_state":{"pump":row["pump_state"] or "UNKNOWN",
                              "grow_light":row["grow_light_state"] or "UNKNOWN"}}

@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.get("/api/plant/latest-image")
def latest_image():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con:
        image_id=request.args.get("image_id")
        if image_id is not None:
            try: image_id=int(image_id)
            except ValueError: return jsonify({"error":"image_id must be integer"}),400
            row=con.execute("SELECT image_path FROM plant_images WHERE device_id=? AND id=?",(device,image_id)).fetchone()
        else: row=con.execute(
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

@app.get("/api/plant/latest-image-info")
def latest_image_info():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con:
        row=con.execute("SELECT id,created_at FROM plant_images WHERE device_id=? ORDER BY id DESC LIMIT 1",(device,)).fetchone()
    if not row: return jsonify({"message":"no image found"}),404
    return jsonify({"image_id":row["id"],"device_id":device,"received_at":row["created_at"],
                    "image_url":"/api/plant/latest-image"})

@app.post("/api/plant/snapshot")
def snapshot():
    if not authorized(): return jsonify({"error":"unauthorized"}),401
    try:
        if "image" not in request.files: return jsonify({"error":"image file required"}),400
        device,species,readings=context_from(request.form)
        pump,light=actuator_states(request.form)
        run_ai=request.form.get("run_analysis","true").lower()
        if run_ai not in ("true","false"): raise ValueError("run_analysis must be true or false")
        received_at=utc_now()
        image_path,_=validate_and_store_image(request.files["image"],device)
        result=None
        if run_ai=="true":
            result={"plant_species":species,"growth_stage":request.form.get("growth_stage","unknown")[:80],
                    "sensor_data":readings,"actuator_state":{"pump":pump,"grow_light":light},
                    "analysis":{"vlm":{"status":"queued","message":"Image received; AI analysis is queued."}},
                    "ai_status":"queued","recommendation_is_advisory":True}
        saved=save_snapshot(device,species,readings,pump,light,image_path,result,"queued" if result else "not_run",captured_at=received_at)
        if result: start_analysis_worker()
        return jsonify({"status":"stored","ai_status":"queued" if result else "not_requested",**saved}),202 if result else 201
    except ValueError as e: return jsonify({"error":str(e)}),400
    except Exception:
        app.logger.exception("Snapshot upload failed")
        return jsonify({"error":"snapshot_failed"}),500

@app.get("/api/health")
def health(): return jsonify({"service":"PlantSense API","status":"ok","timestamp":datetime.now(timezone.utc).isoformat()})
@app.post("/api/plant/analyze")
def analyze():
    if not authorized(): return jsonify({"error":"unauthorized"}),401
    try:
        if "image" not in request.files: return jsonify({"error":"image file required"}),400
        device,species,readings=context_from(request.form)
        pump,light=actuator_states(request.form)
        captured_at=utc_now()
        image_path,raw=validate_and_store_image(request.files["image"],device)
        ctx={"device_id":device,"plant_species":species,"growth_stage":request.form.get("growth_stage","unknown")[:80],"sensor_readings":readings,"actuator_state":{"pump":pump,"grow_light":light}}
        outputs,status=process_analysis(raw,ctx)
        result={"plant_species":species,"analysis":outputs,"ai_status":status,"sensor_data":readings,"actuator_state":{"pump":pump,"grow_light":light},"recommendation_is_advisory":True}
        result.update(save_snapshot(device,species,readings,pump,light,image_path,result,status,captured_at=captured_at))
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
        pump,light=actuator_states(payload)
        saved=save_snapshot(device,species,readings,pump,light)
        return jsonify({"status":"stored",**saved})
    except (ValueError,TypeError) as e: return jsonify({"error":str(e)}),400
@app.get("/api/plant/latest-data")
def latest_data():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con:
        row=con.execute("SELECT * FROM sensor_readings WHERE device_id=? ORDER BY created_at DESC,id DESC LIMIT 1",(device,)).fetchone()
    if not row: return jsonify({"message":"no telemetry found"}),404
    return jsonify(telemetry_from_row(row))
@app.get("/api/plant/latest")
def latest():
    device=request.args.get("device_id","plantsense-01")
    with connection() as con: row=con.execute("SELECT * FROM ai_analysis WHERE device_id=? ORDER BY id DESC LIMIT 1",(device,)).fetchone()
    if not row: return jsonify({"message":"no analysis found"}),404
    result=json.loads(row["result_json"])
    if row["ai_status"] in ("queued","processing"):
        result["ai_status"]=row["ai_status"]
        result["analysis"]={"vlm":{"status":row["ai_status"],"message":"Image received; AI analysis is pending."}}
    return jsonify({"analysis_id":row["id"],"image_id":row["image_id"],"device_id":row["device_id"],"ai_status":row["ai_status"],"created_at":row["created_at"],"result":result})
@app.get("/api/plant/history")
def history():
    device=request.args.get("device_id","plantsense-01")
    try: limit=min(max(int(request.args.get("limit",100)),1),500)
    except ValueError: return jsonify({"error":"limit must be integer"}),400
    with connection() as con: rows=con.execute("SELECT * FROM sensor_readings WHERE device_id=? ORDER BY created_at DESC,id DESC LIMIT ?",(device,limit)).fetchall()
    # Hide SQL NULL fields from clients; they represent unavailable sensors.
    items=[{k:v for k,v in dict(r).items() if v is not None} for r in rows]
    return jsonify({"device_id":device,"items":items})
if __name__=="__main__":
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    start_analysis_worker()
    app.run(host="0.0.0.0",port=5000,debug=False,threaded=True)
