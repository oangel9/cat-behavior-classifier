import sqlite3
import time
import threading
import os
from datetime import datetime
from gpiozero import MotionSensor
from picamera2 import Picamera2
from signal import pause

# --- Configuration ---
DB_PATH = "/home/angel/catpi/cat_data.db"
DEBOUNCE_SECONDS = 5

ZONES = {
    4: "litter",
    17: "feeding_area",
}

SNAPSHOT_DIR = "/home/angel/catpi/snapshots"
SNAPSHOT_COOLDOWN = 600

# --- Database setup ---
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        zone TEXT NOT NULL,
        motion_state TEXT NOT NULL
    )
""")
conn.commit()

db_lock = threading.Lock()

# --- Camera setup ---
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
camera = Picamera2()
camera.configure(camera.create_still_configuration())
camera.start()

last_snapshot = {zone: 0 for zone in ZONES.values()}

def maybe_snapshot(zone):
    now = time.time()
    if now - last_snapshot[zone] < SNAPSHOT_COOLDOWN:
        return
    last_snapshot[zone] = now
    filename = f"{SNAPSHOT_DIR}/{zone}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    camera.capture_file(filename)

# --- Debounce tracking (only applied to 'motion' events) ---
last_logged = {zone: 0 for zone in ZONES.values()}

def log_event(zone, motion_state):
    now = time.time()

    if motion_state == "motion":
        if now - last_logged[zone] < DEBOUNCE_SECONDS:
            return
        last_logged[zone] = now

    timestamp = datetime.now().isoformat()
    with db_lock:
        conn.execute(
            "INSERT INTO raw_events (timestamp, zone, motion_state) VALUES (?, ?, ?)",
            (timestamp, zone, motion_state)
        )
        conn.commit()
    print(f"{timestamp} | {zone} | {motion_state}")

    if motion_state == "motion" and zone == "feeding_area":
        maybe_snapshot(zone)

# --- Wire up each sensor ---
sensors = {}
for pin, zone in ZONES.items():
    sensor = MotionSensor(pin)
    sensor.when_motion = lambda z=zone: log_event(z, "motion")
    sensor.when_no_motion = lambda z=zone: log_event(z, "clear")
    sensors[pin] = sensor

print("Logger running. Watching zones:", list(ZONES.values()))
pause()
