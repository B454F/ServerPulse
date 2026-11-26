
import sqlite3
import time

from database_v2 import DB_PATH

RETENTION_DAYS = 7

now = int(time.time())
cutoff = now - RETENTION_DAYS * 86400

conn = sqlite3.connect(DB_PATH, timeout=30)

try:
    conn.execute("PRAGMA foreign_keys = ON")

    with conn:
        telemetry = conn.execute("""
            DELETE FROM telemetry
            WHERE received_at < ?
        """, (cutoff,)).rowcount

        sessions = conn.execute("""
            DELETE FROM sessions
            WHERE expires_at <= ?
        """, (now,)).rowcount

        pairing = conn.execute("""
            DELETE FROM pairing_codes
            WHERE expires_at <= ?
        """, (now,)).rowcount

    print("[MAINTENANCE] Completed.")
    print(f"Telemetry removed: {telemetry}")
    print(f"Expired sessions removed: {sessions}")
    print(f"Expired pairing codes removed: {pairing}")

finally:
    conn.close()
