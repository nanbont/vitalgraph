"""
VitalGraph Router: MySQL writer.

Writes vitals time-series readings. See SPEC.md section 5 for schema
and rationale.
"""

import logging
import os

import mysql.connector

log = logging.getLogger(__name__)


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER", "vitaluser"),
        password=os.environ.get("MYSQL_PASSWORD", "vitalpass"),
        database=os.environ.get("MYSQL_DATABASE", "vitalgraph"),
    )


def insert_heartrate(conn, patient_id: str, device_id: str, bpm: int, recorded_at: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vitals_heartrate (patient_id, device_id, bpm, recorded_at) "
        "VALUES (%s, %s, %s, %s)",
        (patient_id, device_id, bpm, recorded_at),
    )
    conn.commit()
    cur.close()


def insert_spo2(conn, patient_id: str, device_id: str, spo2_pct: float, recorded_at: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vitals_spo2 (patient_id, device_id, spo2_pct, recorded_at) "
        "VALUES (%s, %s, %s, %s)",
        (patient_id, device_id, spo2_pct, recorded_at),
    )
    conn.commit()
    cur.close()


def insert_activity(
    conn,
    patient_id: str,
    device_id: str,
    recorded_at: str,
    steps: int | None = None,
    sleep_minutes: int | None = None,
):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vitals_activity (patient_id, device_id, steps, sleep_minutes, recorded_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (patient_id, device_id, steps, sleep_minutes, recorded_at),
    )
    conn.commit()
    cur.close()


def fetch_recent_heartrate(conn, patient_id: str, limit: int = 100):
    """Used by the API layer for rolling-average computation (see SPEC.md section 5)."""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT bpm, recorded_at FROM vitals_heartrate "
        "WHERE patient_id = %s ORDER BY recorded_at DESC LIMIT %s",
        (patient_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_recent_spo2(conn, patient_id: str, limit: int = 100):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT spo2_pct, recorded_at FROM vitals_spo2 "
        "WHERE patient_id = %s ORDER BY recorded_at DESC LIMIT %s",
        (patient_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_all_patients(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT patient_id, name, date_of_birth FROM patients")
    rows = cur.fetchall()
    cur.close()
    return rows
