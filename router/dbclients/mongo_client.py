"""MongoDB writer for alerts and device metadata."""

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
    """notified_doctor_id is already resolved before this is called."""
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


def all_device_metadata(db):
    """All device_metadata documents, fields differ per model."""
    return list(db.device_metadata.find())


def alert_stats_by_patient(db):
    pipeline = [
        {
            "$group": {
                "_id": "$patient_id",
                "total_alerts": {"$sum": 1},
                "heartrate_alerts": {
                    "$sum": {"$cond": [{"$eq": ["$alert_type", "abnormal_heartrate"]}, 1, 0]}
                },
                "spo2_alerts": {
                    "$sum": {"$cond": [{"$eq": ["$alert_type", "low_spo2"]}, 1, 0]}
                },
                "last_alert": {"$max": "$detected_at"},
            }
        },
        {"$sort": {"total_alerts": -1}},
    ]
    return list(db.alerts.aggregate(pipeline))


def patients_alerted_within_hour(db, patient_id_1: str, patient_id_2: str) -> bool:
    pipeline = [
        {"$match": {"patient_id": {"$in": [patient_id_1, patient_id_2]}}},
        {"$group": {
            "_id": "$patient_id",
            "latest_alert": {"$max": "$detected_at"}
        }}
    ]
    results = list(db.alerts.aggregate(pipeline))
    if len(results) < 2:
        return False
    times = [r["latest_alert"] for r in results]
    diff = abs((times[0] - times[1]).total_seconds())
    return diff <= 600
