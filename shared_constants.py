"""
VitalGraph: shared constants.

These IDs MUST match exactly what's seeded in:
  - db/mysql/init.sql      (patients, devices tables)
  - db/mongo/seed.js       (device_metadata collection)
  - db/neo4j/seed.cypher   (Patient, Device nodes)

If you add a new patient/device here, you must add it to all three seeds too.
"""

PATIENTS = {
    "11111111-1111-1111-1111-111111111111": {
        "name": "Alice Romano",
        "device_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "device_type": "smartwatch",
        "capabilities": ["heartrate", "spo2", "steps", "sleep"],
    },
    "22222222-2222-2222-2222-222222222222": {
        "name": "Marco Bellini",
        "device_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "device_type": "chest_strap",
        "capabilities": ["heartrate"],  # chest straps don't track spo2/steps/sleep
    },
    "33333333-3333-3333-3333-333333333333": {
        "name": "Sara Conti",
        "device_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "device_type": "smartwatch",
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
