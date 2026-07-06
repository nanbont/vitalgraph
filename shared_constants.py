"""
VitalGraph: shared constants.

These IDs MUST match exactly what's seeded in:
  - db/mysql/init.sql      (patients, devices tables)
  - db/mongo/seed.js       (device_metadata collection)
  - db/neo4j/seed.cypher   (Patient, Device nodes)

If you add a new patient/device here, you must add it to all three seeds too.

Patient IDs follow the Italian Codice Fiscale shape (16 chars: surname/given
name consonant codes + birth year/month/day+sex + birthplace code F158 =
Messina + checksum letter). Device IDs follow a manufacturer-model-serial
convention. Doctor IDs follow a hospital staff-code convention
(MED-<department>-<number>).
"""

PATIENTS = {
    "BKLTST85C54F158P": {
        "name": "Tigist Bekele",
        "device_id": "WXP-6305",
        "device_type": "Apple Watch Series 9",
        "capabilities": ["heartrate", "spo2", "steps", "sleep"],
    },
    "HLADWT72S02F158E": {
        "name": "Dawit Haile",
        "device_id": "CSE-3471",
        "device_type": "Polar H10",
        "capabilities": ["heartrate"],
    },
    "GRMHWT90L62F158Y": {
        "name": "Hiwot Girma",
        "device_id": "WXL-7468",
        "device_type": "Fitbit Charge 6",
        "capabilities": ["heartrate", "spo2", "steps"],
    },
    "BKLBDA88E19F158V": {
        "name": "Abdi Bekele",
        "device_id": "WXP-1791",
        "device_type": "Apple Watch Series 9",
        "capabilities": ["heartrate", "spo2", "steps", "sleep"],
    },
    "BRHBNT95P48F158M": {
        "name": "Abinat Birhanu",
        "device_id": "WXL-2186",
        "device_type": "Fitbit Charge 6",
        "capabilities": ["heartrate", "spo2", "steps"],
    },
}

# MQTT topic structure — see SPEC.md section 4
MQTT_TOPIC_PREFIX = "vitalgraph"


def topic_heartrate(patient_id: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{patient_id}/vitals/heartrate"


def topic_spo2(patient_id: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{patient_id}/vitals/spo2"


def topic_steps(patient_id: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{patient_id}/vitals/steps"


def topic_sleep(patient_id: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{patient_id}/vitals/sleep"


def topic_device_status(patient_id: str) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{patient_id}/device/status"


# Anomaly thresholds — see SPEC.md section 8
HR_HIGH_THRESHOLD = 140
HR_LOW_THRESHOLD = 40
SPO2_LOW_THRESHOLD = 92.0
