import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH

def init_db():
    with sqlite3.connect(DATABASE_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS sensor_readings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, plant_species TEXT,
        temperature_c REAL, humidity_pct REAL, soil_moisture_pct REAL, light_lux REAL,
        pump_state TEXT, grow_light_state TEXT, created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS plant_images(
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, image_path TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS ai_analysis(
        id INTEGER PRIMARY KEY AUTOINCREMENT, image_id INTEGER, device_id TEXT NOT NULL,
        result_json TEXT NOT NULL, ai_status TEXT NOT NULL, created_at TEXT NOT NULL)""")
        con.commit()
@contextmanager
def connection():
    con=sqlite3.connect(DATABASE_PATH);con.row_factory=sqlite3.Row
    try:
        yield con;con.commit()
    finally: con.close()
