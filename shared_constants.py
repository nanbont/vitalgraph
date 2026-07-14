
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


HR_HIGH_THRESHOLD = 140
HR_LOW_THRESHOLD = 40
SPO2_LOW_THRESHOLD = 92.0
