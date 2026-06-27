"""MQTT subscriber, dispatches messages to MySQL/MongoDB/Neo4j, checks anomalies."""

import json
import logging
import os
import sys
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from shared_constants import PATIENTS

sys.path.append(str(Path(__file__).resolve().parent))
from anomaly import check_heartrate, check_spo2
from dbclients import mongo_client, mysql_client, neo4j_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [router] %(message)s")
log = logging.getLogger(__name__)

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC_FILTER = "vitalgraph/+/+/#"


def device_id_for_patient(patient_id: str) -> str | None:
    profile = PATIENTS.get(patient_id)
    return profile["device_id"] if profile else None


def handle_anomaly(
    mongo_db,
    neo4j_driver,
    patient_id: str,
    device_id: str,
    anomaly: dict,
):
    """Resolve who to notify via Neo4j, write the alert to MongoDB."""
    resolution = neo4j_client.resolve_notified_doctor(neo4j_driver, patient_id)
    notified_doctor_id = resolution["doctor_id"] if resolution else None

    alert_id = mongo_client.insert_alert(
        mongo_db,
        patient_id=patient_id,
        device_id=device_id,
        alert_type=anomaly["alert_type"],
        severity=anomaly["severity"],
        detail=anomaly["detail"],
        notified_doctor_id=notified_doctor_id,
    )

    patient_name = PATIENTS.get(patient_id, {}).get("name", patient_id)
    if resolution:
        log.warning(
            "ALERT [%s] patient=%s %s -> notifying %s (primary: %s) [alert_id=%s]",
            anomaly["severity"].upper(),
            patient_name,
            anomaly["alert_type"],
            resolution["doctor_name"],
            resolution["primary_doctor_name"],
            alert_id,
        )
    else:
        log.warning(
            "ALERT [%s] patient=%s %s -> NO DOCTOR FOUND TO NOTIFY [alert_id=%s]",
            anomaly["severity"].upper(),
            patient_name,
            anomaly["alert_type"],
            alert_id,
        )


def make_on_message(mysql_conn, mongo_db, neo4j_driver):
    def on_message(client, userdata, msg):
        parts = msg.topic.split("/")
        # vitalgraph/{patient_id}/{category}/{subtype}
        if len(parts) < 3:
            log.warning("Ignoring malformed topic: %s", msg.topic)
            return

        _, patient_id, category = parts[0], parts[1], parts[2]
        subtype = parts[3] if len(parts) > 3 else None
        device_id = device_id_for_patient(patient_id)
        if device_id is None:
            log.warning("Unknown patient_id in topic: %s", patient_id)
            return

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.error("Malformed JSON payload on topic %s", msg.topic)
            return

        if category == "vitals" and subtype == "heartrate":
            bpm = payload["bpm"]
            mysql_client.insert_heartrate(
                mysql_conn, patient_id, device_id, bpm, payload["recorded_at"]
            )
            anomaly = check_heartrate(bpm)
            if anomaly:
                handle_anomaly(mongo_db, neo4j_driver, patient_id, device_id, anomaly)

        elif category == "vitals" and subtype == "spo2":
            spo2_pct = payload["spo2_pct"]
            mysql_client.insert_spo2(
                mysql_conn, patient_id, device_id, spo2_pct, payload["recorded_at"]
            )
            anomaly = check_spo2(spo2_pct)
            if anomaly:
                handle_anomaly(mongo_db, neo4j_driver, patient_id, device_id, anomaly)

        elif category == "vitals" and subtype == "steps":
            mysql_client.insert_activity(
                mysql_conn, patient_id, device_id, payload["recorded_at"],
                steps=payload["steps"],
            )

        elif category == "vitals" and subtype == "sleep":
            mysql_client.insert_activity(
                mysql_conn, patient_id, device_id, payload["recorded_at"],
                sleep_minutes=payload["sleep_minutes"],
            )

        elif category == "device" and subtype == "status":
            mongo_client.update_device_last_seen(
                mongo_db, device_id, payload["battery_pct"]
            )

        else:
            log.warning("Unhandled topic shape: %s", msg.topic)

    return on_message


def main():
    log.info("Connecting to MySQL...")
    mysql_conn = mysql_client.get_connection()

    log.info("Connecting to MongoDB...")
    mongo_cli = mongo_client.get_client()
    mongo_db = mongo_client.get_db(mongo_cli)

    log.info("Connecting to Neo4j...")
    neo4j_driver = neo4j_client.get_driver()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = make_on_message(mysql_conn, mongo_db, neo4j_driver)

    log.info("Connecting to MQTT broker at %s:%s", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.subscribe(TOPIC_FILTER)
    log.info("Subscribed to %s. Waiting for messages... Ctrl+C to stop.", TOPIC_FILTER)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        log.info("Stopping router.")
    finally:
        client.disconnect()
        mysql_conn.close()
        mongo_cli.close()
        neo4j_driver.close()


if __name__ == "__main__":
    main()
