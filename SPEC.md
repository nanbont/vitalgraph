# VitalGraph — Polyglot Health Monitoring & Care-Network Platform

**Course:** Database Module B
**Track:** DB-B8 — Health & Wellness
**Stack:** Python, MySQL, MongoDB, Neo4j, MQTT (Mosquitto), FastAPI

---

## 1. Concept

VitalGraph simulates wearable health devices streaming vitals over MQTT. A
Python ingestion service routes each message to the database that genuinely
fits its data shape — not as a forced exercise in touching three databases,
but because each one solves a problem the others handle poorly.

The differentiating idea: **Neo4j is not a data store for events — it's a
real-time decision engine.** When an anomaly is detected, the system queries
the care-network graph to decide *who should be notified*, traversing
escalation chains that are awkward in SQL and natural in Cypher. The graph
holds relationships, not records.

---

## 2. Architecture

```
[Simulated Wearables] --(MQTT)--> [Mosquitto Broker]
                                        |
                                        v
                          [Python Ingestion/Router Service]
                           /                              \
                          v                                v
                   MySQL                              MongoDB
              (vitals time-series)          (symptom logs, device metadata,
                                                    alert records)
                          \                                /
                           \                              /
                            v                            v
                         [Anomaly Detector] --query--> Neo4j
                                                  (care network: who to notify)
                                        |
                                        v
                          [FastAPI backend] <-- queries all 3 DBs
                                        |
                                        v
                 [Dashboard: live vitals chart + alert feed + escalation view]
```

---

## 3. Why each database — the honest version

| Data | Database | Why it's natural, not forced |
|---|---|---|
| Heart rate, SpO2, steps, sleep (regular numeric time-series) | **MySQL** | Fixed schema, high-frequency, needs fast range/aggregate queries (rolling averages, daily trends). This is the standard OLTP case for sensor data. |
| Free-text symptom logs, device capability/firmware metadata | **MongoDB** | No two device models share a schema (different sensors, firmware structures, capability sets); patient self-reports are free-form and optional-field-heavy. Forcing either into fixed SQL columns means constant migrations or sparse nullable columns. |
| Care escalation chains, cross-patient device/alert correlation | **Neo4j** | The actual questions asked — "who's next in the escalation chain," "which patients cluster around a failing device model" — are path-traversal questions of variable depth. Awkward as recursive SQL CTEs, natural as Cypher. The graph is queried *at decision time*, not used as a passive event log. |

**Explicitly avoided as decorative:** storing every alert as a Neo4j node.
An alert is an event record — it belongs in MongoDB. The graph is consulted
*when* an alert fires, to traverse existing relationships and decide
routing. This keeps the graph's role honest: relationships, not records.

### Why MySQL specifically (not PostgreSQL or SQLite)

- The reference DB-B8 repo used SQLite, which lacks a real client-server
  story (no concurrent writes, no network access) — too thin for a
  "production-minded" narrative.
- We considered PostgreSQL first, for its native `TIMESTAMPTZ` and
  time-based window functions (`RANGE BETWEEN INTERVAL`). We switched to
  **MySQL** to match the ecosystem the course's reference projects already
  use (the environmental-monitoring reference repo uses MySQL), reducing
  friction during review/defense.
- **Trade-off, made explicit rather than hidden:** MySQL 8's window
  functions support `ROWS BETWEEN` (row-count windows) but not Postgres-style
  time-based `RANGE BETWEEN INTERVAL`. Rolling averages over a *time* window
  (e.g. "last 10 minutes") are therefore computed in the **Python API layer**
  instead of pure SQL — see Section 5's note and the API service. This is a
  legitimate engineering choice (portability, easier to unit test) and is
  called out directly in the report rather than glossed over.
- Timestamps are stored as `DATETIME` in UTC; the application layer is
  responsible for timezone conversion, since MySQL's timezone handling is
  less explicit than Postgres's `TIMESTAMPTZ`.

---

## 4. MQTT topic design

```
vitalgraph/{patient_id}/vitals/heartrate
vitalgraph/{patient_id}/vitals/spo2
vitalgraph/{patient_id}/vitals/sleep
vitalgraph/{patient_id}/vitals/steps
vitalgraph/{patient_id}/symptoms/report
vitalgraph/{patient_id}/device/status
```

The router subscribes to `vitalgraph/+/+/#`. Dispatch is driven by topic
segments (which database/table a message goes to), not by inspecting
payload content — this keeps routing logic explicit and inspectable.

Note: there is no `events/fall` or `events/anomaly` topic published by
devices. Anomalies are *derived* by the router after vitals are written,
not reported by the simulated device itself — this is more realistic
(devices report raw readings; the backend decides what's abnormal).

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

**Rolling average — computed in Python, not SQL.** MySQL 8's window
functions support `ROWS BETWEEN` (row-count windows) but not Postgres-style
time-based `RANGE BETWEEN INTERVAL`. Rather than approximate with a
row-count window (which breaks if readings arrive at irregular intervals),
the API fetches recent raw rows and computes the time-windowed average in
Python:

```python
# api/services/vitals.py (illustrative)
from datetime import timedelta
from statistics import mean

def rolling_avg_bpm(readings: list[dict], window_minutes: int = 10) -> list[dict]:
    """
    readings: list of {"recorded_at": datetime, "bpm": int}, sorted ascending.
    Returns each reading annotated with the average bpm over the preceding window.
    """
    window = timedelta(minutes=window_minutes)
    result = []
    for i, r in enumerate(readings):
        cutoff = r["recorded_at"] - window
        in_window = [x["bpm"] for x in readings[: i + 1] if x["recorded_at"] >= cutoff]
        result.append({**r, "rolling_avg_bpm": round(mean(in_window), 1)})
    return result
```

This is simple, easy to unit test, and is an explicit, defensible trade-off
rather than a workaround glossed over in the report.

---

## 6. MongoDB collections

```js
// device_metadata — varies per manufacturer/model, no fixed schema
{
  "_id": "device-uuid",
  "model": "WearableX Pro",
  "firmware_version": "2.3.1",
  "battery_pct": 78,
  "last_seen": ISODate(),
  "capabilities": ["heartrate", "spo2", "gps"]   // shape differs per device
}

// symptom_logs — free text, optional fields, inherently irregular
{
  "_id": ObjectId(),
  "patient_id": "uuid",
  "reported_at": ISODate(),
  "text": "Felt dizzy after climbing stairs, lasted ~10 min",
  "tags": ["dizziness"],          // optional, patient-entered
  "severity_self_rated": 3        // optional, not all reports include this
}

// alerts — event records, NOT graph nodes (see section 3)
{
  "_id": ObjectId(),
  "patient_id": "uuid",
  "device_id": "uuid",
  "alert_type": "abnormal_heartrate",   // or "low_spo2"
  "severity": "high",
  "detail": { "bpm": 162, "threshold": 140 },  // shape varies by alert_type
  "detected_at": ISODate(),
  "notified_doctor_id": "uuid",          // filled in after Neo4j lookup
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
(:Doctor)-[:BACKUP_FOR]->(:Doctor)      // covering doctor if primary off-duty
(:Patient)-[:OWNS]->(:Device {id, type})  // lightweight, for correlation queries
```

No `Alert` nodes — alerts live in MongoDB. The graph is queried at alert
time, not written to.

### Query 1 — escalation routing (the core "smart" feature)

```cypher
// Find who to notify: primary doctor if on duty, else walk the backup chain.
// Semantics: (X)-[:BACKUP_FOR]->(Y) means "X is the backup for Y", so the
// chain is walked BACKWARDS from the primary doctor to find a covering doctor.
MATCH (p:Patient {id: $patientId})-[:MONITORED_BY]->(primary:Doctor)
OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
RETURN coalesce(available, primary) AS notify, length(path) AS chain_depth
ORDER BY chain_depth
LIMIT 1;
```

This is run by the router the moment an anomaly is detected — the result
becomes `notified_doctor_id` in the MongoDB alert record.

### Query 2 — doctor's current patient load

```cypher
MATCH (doc:Doctor {id: $doctorId})<-[:MONITORED_BY]-(p:Patient)
RETURN p.name, p.id;
```

### Query 3 — device-failure correlation (analytical insight)

```cypher
// Patients sharing a device model who both triggered alerts within the same hour
// — a real signal for a potentially faulty device batch
MATCH (p1:Patient)-[:OWNS]->(d1:Device)
MATCH (p2:Patient)-[:OWNS]->(d2:Device)
WHERE d1.type = d2.type AND p1.id < p2.id
RETURN p1.name, p2.name, d1.type;
```
(Timestamp correlation against MongoDB alert data happens in the API layer,
joining this result with `alerts.detected_at` — a genuine example of
cross-database query composition worth highlighting in the report.)

---

## 8. Anomaly detection logic

Runs in the router immediately after a vitals write to MySQL:

- Heart rate > 140 or < 40 bpm → `abnormal_heartrate`
- SpO2 < 92% → `low_spo2`

On trigger:
1. Run Neo4j escalation query (Section 7, Query 1) → get `notified_doctor_id`
2. Write alert document to MongoDB `alerts` (Section 6), including the
   resolved doctor
3. Push to dashboard via WebSocket

---

## 9. Tech stack

- **Python**: `paho-mqtt`, `mysql-connector-python`/SQLAlchemy, `pymongo`, `neo4j` driver
- **FastAPI**: REST endpoints + WebSocket for live alert push
- **MySQL, MongoDB, Neo4j**: Dockerized
- **Frontend**: lightweight (HTML/JS + Chart.js, or a small React app) —
  live vitals chart, alert feed, escalation chain view
- **Mosquitto**: MQTT broker
- **Docker Compose**: orchestrates everything

---

## 10. Repo structure

```
vitalgraph/
├── publisher/            # simulator: fake wearables publishing to MQTT
├── router/                # subscriber + dispatch + anomaly detection
├── api/                    # FastAPI app
├── dashboard/              # frontend
├── db/
│   ├── mysql/init.sql
│   ├── mongo/seed.js
│   └── neo4j/seed.cypher
├── tests/
├── report/                 # PDF report + screenshots
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 11. One-week plan

| Day | Task |
|---|---|
| 1 | Docker Compose up (MySQL, Mongo, Neo4j, Mosquitto); schemas + seed data (patients, doctors, care teams, devices) |
| 2 | Publisher (simulator) + router skeleton; MQTT → MySQL path working end-to-end |
| 3 | Anomaly detection + Neo4j escalation query + MongoDB alert writes |
| 4 | FastAPI endpoints (vitals history, alerts feed, escalation/graph queries) + WebSocket push |
| 5 | Dashboard: live chart, alert feed, escalation chain view |
| 6 | Polish, tests, README, architecture diagram, bug fixes from self-demo |
| 7 | Buffer + PDF report + screenshots |
