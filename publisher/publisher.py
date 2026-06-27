"""Simulates wearables publishing vitals over MQTT. Run: python publisher/publisher.py"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from shared_constants import (
    PATIENTS,
    topic_device_status,
    topic_heartrate,
    topic_sleep,
    topic_spo2,
    topic_steps,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [publisher] %(message)s"
)
log = logging.getLogger(__name__)

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

# How often each patient's device publishes a heart-rate reading.
MIN_INTERVAL_SECONDS = 10
MAX_INTERVAL_SECONDS = 30
MAX_TICKS = 50

# Roughly 1 in N readings is anomalous. Tuned so a 3-patient demo run of a
# few minutes will reliably show at least one alert without every reading
# being one (see module docstring).
ANOMALY_CHANCE = 1 / 12

# steps/sleep/spo2 don't need to publish as often as heart rate.
SPO2_EVERY_N_HEARTRATE_READINGS = 3
ACTIVITY_EVERY_N_HEARTRATE_READINGS = 6


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_heartrate_reading(force_anomaly: bool = False) -> dict:
    if force_anomaly or random.random() < ANOMALY_CHANCE:
        # Half the time spike high, half the time drop low.
        bpm = random.choice(
            [random.randint(145, 175), random.randint(25, 38)]
        )
    else:
        bpm = random.randint(60, 95)
    return {"bpm": bpm, "recorded_at": now_iso()}


def make_spo2_reading(force_anomaly: bool = False) -> dict:
    if force_anomaly or random.random() < ANOMALY_CHANCE:
        spo2_pct = round(random.uniform(85.0, 91.5), 1)
    else:
        spo2_pct = round(random.uniform(95.0, 99.5), 1)
    return {"spo2_pct": spo2_pct, "recorded_at": now_iso()}


def make_steps_reading() -> dict:
    return {"steps": random.randint(0, 400), "recorded_at": now_iso()}


def make_sleep_reading() -> dict:
    return {"sleep_minutes": random.randint(0, 90), "recorded_at": now_iso()}


def make_device_status(device_type: str, battery_pct: int) -> dict:
    return {
        "device_type": device_type,
        "battery_pct": battery_pct,
        "last_seen": now_iso(),
    }


class PatientSimulator:
    """Tracks publish counters + battery drain for one patient's device."""

    def __init__(self, patient_id: str, profile: dict):
        self.patient_id = patient_id
        self.profile = profile
        self.heartrate_count = 0
        self.battery_pct = random.randint(60, 100)

    def tick(self, client: mqtt.Client):
        caps = self.profile["capabilities"]

        # Heart rate: every device has it, this is the "tick" driver.
        if "heartrate" in caps:
            reading = make_heartrate_reading()
            client.publish(
                topic_heartrate(self.patient_id), json.dumps(reading)
            )
            log.info(
                "patient=%s device=%s bpm=%s",
                self.profile["name"],
                self.profile["device_type"],
                reading["bpm"],
            )
            self.heartrate_count += 1

        # SpO2: less frequent, only if the device supports it.
        if (
            "spo2" in caps
            and self.heartrate_count % SPO2_EVERY_N_HEARTRATE_READINGS == 0
        ):
            reading = make_spo2_reading()
            client.publish(topic_spo2(self.patient_id), json.dumps(reading))
            log.info(
                "patient=%s spo2=%s",
                self.profile["name"],
                reading["spo2_pct"],
            )

        # Steps / sleep: even less frequent, only if supported.
        if (
            "steps" in caps
            and self.heartrate_count % ACTIVITY_EVERY_N_HEARTRATE_READINGS == 0
        ):
            client.publish(
                topic_steps(self.patient_id), json.dumps(make_steps_reading())
            )
        if (
            "sleep" in caps
            and self.heartrate_count % ACTIVITY_EVERY_N_HEARTRATE_READINGS == 0
        ):
            client.publish(
                topic_sleep(self.patient_id), json.dumps(make_sleep_reading())
            )

        # Device status: battery slowly drains, published every tick.
        self.battery_pct = max(1, self.battery_pct - random.choice([0, 0, 1]))
        client.publish(
            topic_device_status(self.patient_id),
            json.dumps(
                make_device_status(self.profile["device_type"], self.battery_pct)
            ),
        )


def main():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    log.info("Connecting to MQTT broker at %s:%s", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    simulators = [
        PatientSimulator(patient_id, profile)
        for patient_id, profile in PATIENTS.items()
    ]

    log.info("Publishing vitals for %d patients, %d ticks max. Ctrl+C to stop early.", len(simulators), MAX_TICKS)
    try:
        for tick_number in range(MAX_TICKS):
            for sim in simulators:
                sim.tick(client)
            time.sleep(random.randint(MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS))
        log.info("Reached tick limit, stopping.")
    except KeyboardInterrupt:
        log.info("Stopping publisher.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
