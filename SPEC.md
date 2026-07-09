# VitalGraph — Technical Specification

**Course:** Database Management Systems, Module B
**Track:** DB-B8 — Health & Wellness
**Stack:** Python, MySQL, MongoDB, Neo4j, MQTT (Mosquitto), FastAPI, Streamlit

---

## 1. Concept

Simulated wearable devices publish vital signs over MQTT. A Python subscriber routes each message to the database best suited for that type of data: MySQL for structured numeric time-series, MongoDB for variable-structure alerts and device metadata, and Neo4j for the care network of patients and doctors.

Neo4j is queried live when an alert fires to resolve which doctor to notify, walking a backup chain of up to two hops if the primary doctor is unavailable. The graph holds relationships and is never written to as part of normal operation.

---

## 2. Architecture

```
[Publisher: Simulated Wearables] --(MQTT)--> [Mosquitto Broker]
                                                      |
                                                      v
                                          [Python Subscriber]
                                        /         |          \
                                       v          v           v
                                   MySQL      MongoDB       Neo4j
                             (vitals,       (alerts,      (care network,
                              anomaly log,   device        escalation
                              view, procs)   metadata)     queries)
                                       \         |          /
                                        v        v         v
                                       [FastAPI Backend]
                                                |
                                                v
                                    [Streamlit Dashboard]
```

---

## 3. Why each database

| Data | Database | Reasoning |
|---|---|---|
| Heart rate, SpO2, steps, sleep | MySQL | Fixed schema, high write frequency, needs fast range queries. Standard relational case for sensor time-series. |
| Alert records, device metadata | MongoDB | Alert detail field differs by alert type. Device metadata differs by model. Neither fits a fixed relational schema without sparse nullable columns. |
| Care escalation chains, device correlation | Neo4j | Variable-depth path traversal questions. Natural in Cypher, queried live at decision time. |

No Alert nodes in Neo4j. An alert is an event with a timestamp and a payload, and that belongs in MongoDB. The graph changes only when the care network itself changes: a doctor's duty status, a new backup assignment.

### Why MySQL instead of PostgreSQL

Started with PostgreSQL for native TIMESTAMPTZ and time-based window functions (RANGE BETWEEN INTERVAL). Switched to MySQL to align with the course ecosystem. Cost: MySQL 8 supports ROWS BETWEEN (row-count windows) but not time-based RANGE BETWEEN INTERVAL. The rolling average was moved into Python as a result.

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

Subscriber uses a single wildcard subscription: `vitalgraph/+/+/#`. Routing is based on topic segments, not payload inspection.

There is no `events/anomaly` topic. Devices publish raw readings. The subscriber decides what counts as abnormal after the write.

---

## 5. MySQL schema

Core tables:

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
```

vitals_spo2 and vitals_activity follow the same pattern.

### Trigger

Fires after every INSERT into vitals_heartrate and vitals_spo2. Logs anomalous readings to anomaly_log automatically, independent of Python code:

```sql
CREATE TRIGGER trg_heartrate_anomaly
AFTER INSERT ON vitals_heartrate
FOR EACH ROW
BEGIN
    IF NEW.bpm > 140 THEN
        INSERT INTO anomaly_log (patient_id, device_id, reading_type, value, direction, threshold)
        VALUES (NEW.patient_id, NEW.device_id, 'heartrate', NEW.bpm, 'high', 140);
    ELSEIF NEW.bpm < 40 THEN
        INSERT INTO anomaly_log (patient_id, device_id, reading_type, value, direction, threshold)
        VALUES (NEW.patient_id, NEW.device_id, 'heartrate', NEW.bpm, 'low', 40);
    END IF;
END
```

### View

Joins patients with their latest vitals and total anomaly count:

```sql
CREATE VIEW patient_vitals_summary AS
SELECT p.patient_id, p.name, p.date_of_birth,
    hr.bpm AS latest_bpm,
    s.spo2_pct AS latest_spo2,
    COUNT(a.id) AS total_anomalies
FROM patients p
LEFT JOIN vitals_heartrate hr ON hr.patient_id = p.patient_id
    AND hr.recorded_at = (SELECT MAX(recorded_at) FROM vitals_heartrate WHERE patient_id = p.patient_id)
LEFT JOIN vitals_spo2 s ON s.patient_id = p.patient_id
    AND s.recorded_at = (SELECT MAX(recorded_at) FROM vitals_spo2 WHERE patient_id = p.patient_id)
LEFT JOIN anomaly_log a ON a.patient_id = p.patient_id
GROUP BY p.patient_id, p.name, p.date_of_birth, hr.bpm, hr.recorded_at, s.spo2_pct, s.recorded_at;
```

### Stored procedure

Returns latest vitals and recent anomaly history for one patient:

```sql
CREATE PROCEDURE get_patient_summary(IN p_id CHAR(36))
BEGIN
    SELECT p.name, p.date_of_birth, hr.bpm AS latest_bpm, s.spo2_pct AS latest_spo2
    FROM patients p
    LEFT JOIN vitals_heartrate hr ON hr.patient_id = p.patient_id
        AND hr.recorded_at = (SELECT MAX(recorded_at) FROM vitals_heartrate WHERE patient_id = p_id)
    LEFT JOIN vitals_spo2 s ON s.patient_id = p.patient_id
        AND s.recorded_at = (SELECT MAX(recorded_at) FROM vitals_spo2 WHERE patient_id = p_id)
    WHERE p.patient_id = p_id;

    SELECT reading_type, value, direction, threshold, logged_at
    FROM anomaly_log
    WHERE patient_id = p_id
    ORDER BY logged_at DESC LIMIT 5;
END
```

### Archive procedure and event

Moves readings older than 30 minutes to vitals_heartrate_archive. Runs automatically every 30 minutes via MySQL Event Scheduler:

```sql
CREATE PROCEDURE archive_old_readings()
BEGIN
    INSERT INTO vitals_heartrate_archive
        SELECT * FROM vitals_heartrate
        WHERE recorded_at < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 MINUTE);
    DELETE FROM vitals_heartrate
        WHERE recorded_at < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 MINUTE);
    SELECT ROW_COUNT() AS rows_archived;
END

CREATE EVENT auto_archive
ON SCHEDULE EVERY 30 MINUTE
DO CALL archive_old_readings();
```

### Rolling average (Python)

MySQL 8 does not support time-based RANGE BETWEEN INTERVAL, so the rolling average is computed in Python:

```python
from datetime import timedelta
from statistics import mean

def rolling_avg_bpm(readings: list[dict], window_minutes: int = 10) -> list[dict]:
    # average over the preceding time window, not row count
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
// device_metadata — shape differs per device model
{
  "_id": "WXP-6305",
  "model": "Apple Watch Series 9",
  "firmware_version": "10.3.1",
  "battery_pct": 78,
  "last_seen": ISODate(),
  "capabilities": ["heartrate", "spo2", "steps", "sleep"]
}

// symptom_logs — free text, optional fields
{
  "_id": ObjectId(),
  "patient_id": "BKLTST85C54F158P",
  "reported_at": ISODate(),
  "text": "Felt dizzy after climbing stairs, lasted about 10 minutes",
  "tags": ["dizziness"],
  "severity_self_rated": 3
}

// alerts — event records, not graph nodes
{
  "_id": ObjectId(),
  "patient_id": "BKLTST85C54F158P",
  "device_id": "WXP-6305",
  "alert_type": "abnormal_heartrate",
  "severity": "high",
  "detail": { "bpm": 162, "threshold": 140, "direction": "high" },
  "detected_at": ISODate(),
  "notified_doctor_id": "MED-CARD-521",
  "acknowledged": false
}
```

### Aggregation pipeline

Groups alerts by patient with heartrate/SpO2 breakdown:

```javascript
db.alerts.aggregate([
  { "$group": {
    "_id": "$patient_id",
    "total_alerts": { "$sum": 1 },
    "heartrate_alerts": { "$sum": { "$cond": [{ "$eq": ["$alert_type", "abnormal_heartrate"] }, 1, 0] } },
    "spo2_alerts": { "$sum": { "$cond": [{ "$eq": ["$alert_type", "low_spo2"] }, 1, 0] } },
    "last_alert": { "$max": "$detected_at" }
  }},
  { "$sort": { "total_alerts": -1 } }
])
```

### TTL index

Expires alert documents older than 30 days automatically:

```javascript
db.alerts.createIndex(
  { detected_at: 1 },
  { expireAfterSeconds: 2592000, name: "ttl_alerts_30days" }
)
```

---

## 7. Neo4j graph model

```cypher
(:Patient {id, name})
(:Doctor {id, name, specialty, on_duty})
(:CareTeam {id, name})

(:Patient)-[:MONITORED_BY]->(:Doctor)
(:Doctor)-[:MEMBER_OF]->(:CareTeam)
(:Doctor)-[:BACKUP_FOR]->(:Doctor)
(:Patient)-[:OWNS]->(:Device {id, type})
```

### Query 1 — escalation routing

Run by the subscriber the instant an anomaly fires. Result becomes notified_doctor_id in the MongoDB alert.

```cypher
// (X)-[:BACKUP_FOR]->(Y) means X backs up Y; walk backwards from primary
MATCH (p:Patient {id: $patientId})-[:MONITORED_BY]->(primary:Doctor)
OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
RETURN coalesce(available, primary) AS notify, length(path) AS chain_depth
ORDER BY chain_depth
LIMIT 1;
```

Current care network exercises all three depth levels:
- Tigist Bekele: chain depth 2 (primary and backup both off duty)
- Dawit Haile: chain depth 1 (primary off duty)
- Hiwot, Abdi, Abinat: chain depth 0 (primary on duty)

The first draft had BACKUP_FOR direction backwards. Caught by hand-tracing the seed data before testing live.

### Query 2 — doctor patient load

```cypher
MATCH (doc:Doctor {id: $doctorId})<-[:MONITORED_BY]-(p:Patient)
RETURN p.name, p.id;
```

### Query 3 — device correlation

```cypher
MATCH (p1:Patient)-[:OWNS]->(d1:Device)
MATCH (p2:Patient)-[:OWNS]->(d2:Device)
WHERE d1.type = d2.type AND p1.id < p2.id
RETURN p1.name, p2.name, d1.type;
```

Result is joined in the API layer against alerts.detected_at from MongoDB to check if paired patients had alerts within the same 10-minute window.

### Query 4 — on-call doctors

```cypher
MATCH (d:Doctor {on_duty: true})
OPTIONAL MATCH (p:Patient)-[:MONITORED_BY]->(d)
RETURN d.name AS doctor, d.specialty AS specialty, count(p) AS patient_count
ORDER BY patient_count DESC
```

---

## 8. Anomaly detection

Runs in the subscriber after every vitals write:

- Heart rate > 160 bpm: severity high
- Heart rate > 140 bpm: severity warning
- Heart rate < 40 bpm: severity high
- SpO2 < 85%: severity high
- SpO2 < 92%: severity warning

On trigger: run escalation query, write alert to MongoDB with notified_doctor_id already resolved, dashboard picks it up.

---

## 9. Patients and doctors

**Patients (5):**
- Tigist Bekele (BKLTST85C54F158P) — Apple Watch Series 9
- Dawit Haile (HLADWT72S02F158E) — Polar H10
- Hiwot Girma (GRMHWT90L62F158Y) — Fitbit Charge 6
- Abdi Bekele (BKLBDA88E19F158V) — Apple Watch Series 9
- Abinat Birhanu (BRHBNT95P48F158M) — Fitbit Charge 6

**Doctors (6):**
- Dr. Selam Tadesse (MED-CARD-343) — Cardiology, off duty
- Dr. Yonas Desta (MED-CARD-706) — Cardiology, off duty
- Dr. Meron Alemu (MED-CARD-657) — General Medicine, on duty
- Dr. Melaku Tafesse (MED-IMED-233) — Internal Medicine, on duty
- Dr. Siduna Girma (MED-IMED-478) — Internal Medicine, on duty
- Dr. Fikirte Hailu (MED-CARD-521) — Cardiology, on duty (backs up Dr. Yonas)

---

## 10. Tech stack

- Python: paho-mqtt, mysql-connector-python, pymongo, neo4j driver, fastapi, streamlit
- All services run in Docker via docker-compose

---

## 11. Repo structure

```
vitalgraph/
├── publisher/publisher.py      simulates five wearable devices
├── router/
│   ├── subscriber.py           MQTT subscriber, dispatcher, anomaly detection
│   ├── anomaly.py              threshold checks (warning vs high severity)
│   └── dbclients/              MySQL, MongoDB, Neo4j client modules
├── api/main.py                 FastAPI backend
├── dashboard_app.py            Streamlit dashboard
├── shared_constants.py         patient/device IDs, MQTT topics, thresholds
├── db/
│   ├── mysql/init.sql          schema, triggers, view, procedures, archive, event
│   ├── mongo/seed.js           device metadata, TTL index
│   └── neo4j/seed.cypher       care network with 6 doctors and backup chains
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```
