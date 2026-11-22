"""Single-process SQLite-backed AI worker; image uploads never wait for Groq."""
import json
import logging
from pathlib import Path
import threading

from database import connection
from services import process_analysis, utc_now

_lock = threading.Lock()
_thread = None
_stop = threading.Event()
logger = logging.getLogger(__name__)


def process_next_analysis():
    with connection() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("""SELECT a.*, p.image_path FROM ai_analysis a
            JOIN plant_images p ON p.id=a.image_id
            WHERE a.ai_status='queued' ORDER BY a.id LIMIT 1""").fetchone()
        if row is None:
            return False
        con.execute("UPDATE ai_analysis SET ai_status='processing' WHERE id=?", (row["id"],))
    result = json.loads(row["result_json"])
    context = {
        "device_id": row["device_id"],
        "plant_species": result["plant_species"],
        "growth_stage": result.get("growth_stage", "unknown"),
        "sensor_readings": result["sensor_data"],
        "actuator_state": result["actuator_state"],
    }
    try:
        outputs, status = process_analysis(Path(row["image_path"]).read_bytes(), context)
        result["analysis"] = outputs
    except Exception:
        logger.exception("Background analysis failed for image %s", row["image_id"])
        status = "failed"
        result["analysis"] = {"vlm": {"status": "failed", "message": "AI analysis failed; check backend logs."}}
    result["ai_status"] = status
    result["completed_at"] = utc_now()
    with connection() as con:
        con.execute("UPDATE ai_analysis SET result_json=?,ai_status=? WHERE id=?",
                    (json.dumps(result), status, row["id"]))
    return True


def _run():
    while not _stop.is_set():
        try:
            if process_next_analysis():
                continue
        except Exception:
            logger.exception("AI queue worker error")
        _stop.wait(0.25)


def start_analysis_worker():
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        # Resume a job interrupted by a previous backend shutdown.
        with connection() as con:
            con.execute("UPDATE ai_analysis SET ai_status='queued' WHERE ai_status='processing'")
            con.execute("""UPDATE ai_analysis SET ai_status='superseded'
                WHERE ai_status='queued' AND id NOT IN
                (SELECT MAX(id) FROM ai_analysis WHERE ai_status='queued' GROUP BY device_id)""")
        _stop.clear()
        _thread = threading.Thread(target=_run, name="plant-ai", daemon=True)
        _thread.start()


def stop_analysis_worker(timeout=5):
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=timeout)
