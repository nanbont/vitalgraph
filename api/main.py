"""VitalGraph FastAPI backend. Run: uvicorn api.main:app --reload --port 8000"""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "router"))
load_dotenv(ROOT / ".env")

from dbclients import mongo_client, mysql_client, neo4j_client  # noqa: E402
from shared_constants import PATIENTS  # noqa: E402

try:
    from rolling_average import with_rolling_average  # noqa: E402
except ImportError:
    from api.rolling_average import with_rolling_average  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [api] %(message)s")
log = logging.getLogger(__name__)

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Connecting to databases...")
    state["mysql"] = mysql_client.get_connection()
    state["mongo_cli"] = mongo_client.get_client()
    state["mongo_db"] = mongo_client.get_db(state["mongo_cli"])
    state["neo4j"] = neo4j_client.get_driver()
    state["ws_clients"] = set()
    log.info("Ready.")
    yield
    log.info("Shutting down database connections...")
    state["mysql"].close()
    state["mongo_cli"].close()
    state["neo4j"].close()


app = FastAPI(title="VitalGraph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a course project, not for production
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_known_patient(patient_id: str):
    if patient_id not in PATIENTS:
        raise HTTPException(status_code=404, detail="Unknown patient_id")


@app.get("/patients")
def list_patients():
    rows = mysql_client.fetch_all_patients(state["mysql"])
    for r in rows:
        if r.get("date_of_birth") is not None:
            r["date_of_birth"] = r["date_of_birth"].isoformat()
    return rows


@app.get("/patients/{patient_id}/vitals/heartrate")
def get_heartrate(patient_id: str, limit: int = 50):
    _require_known_patient(patient_id)
    rows = mysql_client.fetch_recent_heartrate(state["mysql"], patient_id, limit)
    annotated = with_rolling_average(rows, "bpm", window_minutes=10)
    for r in annotated:
        r["recorded_at"] = r["recorded_at"].isoformat()
    return annotated


@app.get("/patients/{patient_id}/vitals/spo2")
def get_spo2(patient_id: str, limit: int = 50):
    _require_known_patient(patient_id)
    rows = mysql_client.fetch_recent_spo2(state["mysql"], patient_id, limit)
    annotated = with_rolling_average(rows, "spo2_pct", window_minutes=10)
    for r in annotated:
        r["recorded_at"] = r["recorded_at"].isoformat()
    return annotated


@app.get("/alerts")
def get_alerts(limit: int = 20, patient_id: str | None = None):
    rows = mongo_client.recent_alerts(state["mongo_db"], patient_id=patient_id, limit=limit)
    result = []
    for r in rows:
        item = dict(r)
        item["_id"] = str(item["_id"])
        item["detected_at"] = item["detected_at"].isoformat()
        item["notified_doctor_name"] = neo4j_client.doctor_name_by_id(
            state["neo4j"], item.get("notified_doctor_id")
        )
        result.append(item)
    return result


@app.get("/patients/{patient_id}/care-network")
def get_care_network(patient_id: str):
    _require_known_patient(patient_id)
    resolution = neo4j_client.resolve_notified_doctor(state["neo4j"], patient_id)
    if resolution is None:
        raise HTTPException(status_code=404, detail="No care network found for patient")
    escalated = resolution["doctor_name"] != resolution["primary_doctor_name"]
    return {**resolution, "escalated": escalated}


@app.get("/insights/device-correlation")
def get_device_correlation():
    return neo4j_client.device_sharing_pairs(state["neo4j"])


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """Polls MongoDB for new alerts and pushes them to the client."""
    await websocket.accept()
    state["ws_clients"].add(websocket)
    last_seen_id = None
    try:
        while True:
            rows = mongo_client.recent_alerts(state["mongo_db"], limit=1)
            if rows:
                newest = rows[0]
                newest_id = str(newest["_id"])
                if newest_id != last_seen_id:
                    last_seen_id = newest_id
                    payload = dict(newest)
                    payload["_id"] = newest_id
                    payload["detected_at"] = payload["detected_at"].isoformat()
                    payload["notified_doctor_name"] = neo4j_client.doctor_name_by_id(
                        state["neo4j"], payload.get("notified_doctor_id")
                    )
                    await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        state["ws_clients"].discard(websocket)
