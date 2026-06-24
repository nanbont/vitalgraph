"""
VitalGraph Router: MongoDB writer.

Writes alerts (event records) and updates device_metadata.last_seen.
See SPEC.md section 6 for rationale — alerts and device metadata live
here because their shape genuinely varies; they are NOT decorative uses
of MongoDB.
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient


def get_client() -> MongoClient:
    host = os.environ.get("MONGO_HOST", "localhost")
    port = int(os.environ.get("MONGO_PORT", 27017))
    user = os.environ.get("MONGO_USER", "vitaluser")
    password = os.environ.get("MONGO_PASSWORD", "vitalpass")
    return MongoClient(
        host=host, port=port, username=user, password=password,
        authSource="admin",
    )


def get_db(client: MongoClient):
    return client[os.environ.get("MONGO_DB", "vitalgraph")]


def insert_alert(
    db,
    patient_id: str,
    device_id: str,
    alert_type: str,
    severity: str,
    detail: dict,
    notified_doctor_id: str | None,
) -> str:
    """
    Insert an alert event record. notified_doctor_id is resolved by the
    router via the Neo4j escalation query BEFORE this is called — the
    graph is consulted at decision time, not used as a data store for
    the alert itself (see SPEC.md section 3 and 7).
    """
    doc = {
        "patient_id": patient_id,
        "device_id": device_id,
        "alert_type": alert_type,
        "severity": severity,
        "detail": detail,
        "detected_at": datetime.now(timezone.utc),
        "notified_doctor_id": notified_doctor_id,
        "acknowledged": False,
    }
    result = db.alerts.insert_one(doc)
    return str(result.inserted_id)


def update_device_last_seen(db, device_id: str, battery_pct: int):
    db.device_metadata.update_one(
        {"_id": device_id},
        {"$set": {
            "battery_pct": battery_pct,
            "last_seen": datetime.now(timezone.utc),
        }},
    )


def recent_alerts(db, patient_id: str | None = None, limit: int = 50):
    query = {"patient_id": patient_id} if patient_id else {}
    return list(
        db.alerts.find(query).sort("detected_at", -1).limit(limit)
    )
