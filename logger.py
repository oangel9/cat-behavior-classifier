import sqlite3
import time
import threading
from datetime import datetime
from gpiozero import MotionSensor
from signal import pause

# --- Configuration ---
DB_PATH = "/home/angel/catpi/cat_data.db"
DEBOUNCE_SECONDS =  5

ZONES = {
    4: "litter",
    17: "food",
    27: "water",
}

# --- Database setup ---
# check_same_thread=False: gpiozero fires callbacks from background threads,
# not the thread that created this connection, so we must allow that.
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

# A lock so two sensor threads can't write to the connection at the exact same instant.
db_lock = threading.Lock()

# --- Debounce tracking ---
last_logged = {zone: 0 for zone in ZONES.values()}

def log_event(zone, motion_state):
    now = time.time()
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

# --- Wire up each sensor ---
sensors = {}
for pin, zone in ZONES.items():
    sensor = MotionSensor(pin)
    sensor.when_motion = lambda z=zone: log_event(z, "motion")
    sensor.when_no_motion = lambda z=zone: log_event(z, "clear")
    sensors[pin] = sensor

print("Logger running. Watching zones:", list(ZONES.values()))
pause()
