# VitalGraph — Polyglot Health Monitoring & Care-Network Platform

**Course:** Database Module B  **Track:** DB-B8 — Health & Wellness
**Stack:** Python, MySQL, MongoDB, Neo4j, MQTT (Mosquitto), FastAPI, Streamlit

---

## 1. Concept

Simulated wearable devices stream vitals over MQTT. A Python router picks
up each message and writes it to whichever database actually fits that
kind of data — MySQL for the regular numeric readings, MongoDB for the
stuff that doesn't have a fixed shape, Neo4j for the care-network
relationships.

The part I actually care about getting right: Neo4j isn't just storing
data, it's used to decide things. When a reading crosses a threshold, the
router queries the graph to figure out who should get notified — walking
a backup-coverage chain if the patient's usual doctor is off duty. The
graph holds relationships; it doesn't log events.

---

## 2. Architecture

```
[Simulated Wearables] --(MQTT)--> [Mosquitto Broker]
                                        |
                                        v
                          [Python Router]
                           /                              \
                          v                                v
                   MySQL                              MongoDB
              (vitals time-series)          (symptom logs, device metadata,
                                                    alert records)
                          \                                /
                           \                              /
                            v                            v
                         [Anomaly check] --query--> Neo4j
                                                  (who to notify)
                                        |
                                        v
                          [FastAPI backend] <-- queries all 3 DBs
                                        |
                                        v
                       [Streamlit dashboard: charts + alert feed]
```

---

## 3. Why each database

| Data | Database | Reasoning |
|---|---|---|
| Heart rate, SpO2, steps, sleep | **MySQL** | Fixed schema, high write frequency, needs fast range/aggregate queries. Standard OLTP case. |
| Symptom logs, device metadata | **MongoDB** | Different device models genuinely have different fields (sensors, firmware, capabilities). Patient self-reports are free-form with optional fields. Either of these as fixed SQL columns means constant migrations. |
| Care escalation chains, device-correlation | **Neo4j** | "Who's next in the escalation chain" and "which patients share a device model" are variable-depth path questions — painful as recursive SQL, natural in Cypher. Queried at decision time, not stored as a log. |

No `Alert` nodes in Neo4j — an alert is an event with a timestamp, that's
MongoDB's job. The graph only gets touched when the care network itself
changes (a doctor's shift status, a new backup assignment).

### Why MySQL and not Postgres or SQLite

Started with Postgres, mainly for `TIMESTAMPTZ` and time-based window
functions (`RANGE BETWEEN INTERVAL`) — would've made rolling averages a
one-liner. Switched to MySQL partway through, since the other DB-B8
submission I looked at for reference used SQLite (no real concurrent
writes, felt too thin), and a different reference project used MySQL
successfully for a similar pipeline.

Cost of the switch: MySQL 8 supports `ROWS BETWEEN` but not time-based
`RANGE BETWEEN INTERVAL`. A row-count window isn't the same thing as a
time window if readings arrive at irregular intervals, so the rolling
average got moved out of SQL and into Python (see Section 5). Timestamps
are stored as UTC `DATETIME`; timezone conversion is the application's
problem, not the database's.

---

## 4. MQTT topics

```
vitalgraph/{patient_id}/vitals/heartrate
vitalgraph/{patient_id}/vitals/spo2
vitalgraph/{patient_id}/vitals/sleep
vitalgraph/{patient_id}/vitals/steps
vitalgraph/{patient_id}/symptoms/report
vitalgraph/{patient_id}/device/status
```

Router subscribes to `vitalgraph/+/+/#`. Routing is based on the topic
segments, not on inspecting the payload.

No `events/anomaly` topic — devices report raw readings, the router
decides what counts as abnormal after the fact. That's closer to how a
real device would actually behave.

---

## 5. MySQL schema

```sql
CREATE TABLE patients (
    patient_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    created_at DATETIME DEFAULT (UTC_TIMESTAMP())
);

CREATE TABLE devices (
    device_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    patient_id CHAR(36),
    device_type VARCHAR(100) NOT NULL,
    registered_at DATETIME DEFAULT (UTC_TIMESTAMP()),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE vitals_heartrate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    bpm INT NOT NULL,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_hr_patient_time ON vitals_heartrate (patient_id, recorded_at DESC);

CREATE TABLE vitals_spo2 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    spo2_pct DECIMAL(4,1) NOT NULL,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_spo2_patient_time ON vitals_spo2 (patient_id, recorded_at DESC);

CREATE TABLE vitals_activity (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    steps INT,
    sleep_minutes INT,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
```

**Rolling average, computed in Python:**

```python
# api/services/vitals.py
from datetime import timedelta
from statistics import mean

def rolling_avg_bpm(readings: list[dict], window_minutes: int = 10) -> list[dict]:
    """readings: [{"recorded_at": datetime, "bpm": int}, ...], sorted ascending."""
    window = timedelta(minutes=window_minutes)
    result = []
    for i, r in enumerate(readings):
        cutoff = r["recorded_at"] - window
        in_window = [x["bpm"] for x in readings[: i + 1] if x["recorded_at"] >= cutoff]
        result.append({**r, "rolling_avg_bpm": round(mean(in_window), 1)})
    return result
```

---

## 6. MongoDB collections

```javascript
// device_metadata — shape varies per manufacturer/model
{
  "_id": "WXP-6305",
  "model": "WearableX Pro",
  "firmware_version": "2.3.1",
  "battery_pct": 78,
  "last_seen": ISODate(),
  "capabilities": ["heartrate", "spo2", "steps", "sleep"]
}

// symptom_logs — free text, optional fields
{
  "_id": ObjectId(),
  "patient_id": "...",
  "reported_at": ISODate(),
  "text": "Felt dizzy after climbing stairs, lasted ~10 min",
  "tags": ["dizziness"],
  "severity_self_rated": 3
}

// alerts — event records, not graph nodes
{
  "_id": ObjectId(),
  "patient_id": "...",
  "device_id": "...",
  "alert_type": "abnormal_heartrate",
  "severity": "high",
  "detail": { "bpm": 162, "threshold": 140, "direction": "high" },
  "detected_at": ISODate(),
  "notified_doctor_id": "...",
  "acknowledged": false
}
```

---

## 7. Neo4j graph model

```cypher
// Nodes
(:Patient {id, name})
(:Doctor {id, name, specialty, on_duty})
(:CareTeam {id, name})

// Relationships
(:Patient)-[:MONITORED_BY]->(:Doctor)
(:Doctor)-[:MEMBER_OF]->(:CareTeam)
(:Doctor)-[:BACKUP_FOR]->(:Doctor)        // covering doctor if primary off-duty
(:Patient)-[:OWNS]->(:Device {id, type})
```

### Query 1 — escalation routing

This is the one that matters. Run by the router the instant an anomaly
fires; the result becomes `notified_doctor_id` in the MongoDB alert.

```cypher
// (X)-[:BACKUP_FOR]->(Y) means "X is the backup for Y" — so walk the
// chain BACKWARDS from the primary to find who's covering for them.
MATCH (p:Patient {id: $patientId})-[:MONITORED_BY]->(primary:Doctor)
OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
RETURN coalesce(available, primary) AS notify, length(path) AS chain_depth
ORDER BY chain_depth
LIMIT 1;
```

First draft of this query had the `BACKUP_FOR` direction backwards —
caught it by tracing a small example by hand against the seed data before
testing live (full story in the report).

### Query 2 — doctor's current patient load

```cypher
MATCH (doc:Doctor {id: $doctorId})<-[:MONITORED_BY]-(p:Patient)
RETURN p.name, p.id;
```

### Query 3 — device-correlation

```cypher
// patients sharing a device model — signal for a faulty device batch
MATCH (p1:Patient)-[:OWNS]->(d1:Device)
MATCH (p2:Patient)-[:OWNS]->(d2:Device)
WHERE d1.type = d2.type AND p1.id < p2.id
RETURN p1.name, p2.name, d1.type;
```

Result gets joined against `alerts.detected_at` from MongoDB in the API
layer to check if the pair's alerts actually cluster in time.

---

## 8. Anomaly detection

Runs in the router right after a vitals write:

- Heart rate > 140 or < 40 bpm → `abnormal_heartrate`
- SpO2 < 92% → `low_spo2`

On trigger: run the Section 7 escalation query → write the alert to
MongoDB with the resolved doctor already attached → dashboard picks it up.

---

## 9. Tech stack

- **Python**: `paho-mqtt`, `mysql-connector-python`, `pymongo`, `neo4j` driver
- **FastAPI**: REST endpoints, independent of the dashboard
- **Streamlit**: dashboard, connects directly to all three databases
- **MySQL, MongoDB, Neo4j, Mosquitto**: Dockerized

(Originally planned a React frontend — abandoned after a few hours
fighting Node version/port issues on this machine, switched to Streamlit.
Not a big loss; one less moving part.)

---

## 10. Repo structure

```
vitalgraph/
├── publisher/publisher.py
├── router/
│   ├── router.py
│   ├── anomaly.py
│   └── dbclients/
├── api/main.py
├── dashboard_app.py
├── shared_constants.py
├── db/
│   ├── mysql/init.sql
│   ├── mongo/seed.js
│   └── neo4j/seed.cypher, load_seed.sh
├── mosquitto/config/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```
