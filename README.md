# VitalGraph

Polyglot health-monitoring platform for the DB-B8 (Health & Wellness) track.

Simulated wearables stream vitals over MQTT. A Python router picks up each
message and writes it into MySQL, MongoDB, or Neo4j depending on what kind
of data it is. When a reading crosses an anomaly threshold, the router
queries Neo4j to figure out who to notify (walking a backup chain if the
patient's primary doctor is off duty) and logs the alert in MongoDB.

Full design rationale, schemas, and the actual Cypher queries are in
[`SPEC.md`](./SPEC.md).

## Status

Everything below works and has been tested against real running data:
Docker stack, publisher, router (with live escalation), FastAPI backend,
Streamlit dashboard.

## Getting started

```bash
cp .env.example .env
docker compose up -d
```

MySQL and Mongo seed themselves on first start. Neo4j doesn't support
auto-running `.cypher` files, so run this once after the containers are up:

```bash
./db/neo4j/load_seed.sh
```

Don't run it twice without wiping the volume first — Cypher's `CREATE`
doesn't dedupe, so re-running the seed just creates duplicate nodes and
relationships on top of the old ones. (Learned this one the hard way.)

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then, two terminals:

```bash
# terminal 1
python router/router.py

# terminal 2
python publisher/publisher.py
```

The router logs an `ALERT` line whenever something fires, including which
doctor got notified. Then:

```bash
streamlit run dashboard_app.py
```

Opens at `http://localhost:8501`. Connects straight to MySQL/Mongo/Neo4j,
no separate API needed for the dashboard itself.

There's also a FastAPI backend (`api/main.py`) if you want REST/WebSocket
access independent of the dashboard:

```bash
uvicorn api.main:app --reload --port 8000
```

## Checking it's actually working

```bash
docker ps
# vitalgraph-mosquitto, vitalgraph-mysql, vitalgraph-mongo, vitalgraph-neo4j

docker exec -it vitalgraph-mysql mysql -u vitaluser -pvitalpass vitalgraph \
  -e "SELECT * FROM patients;"

docker exec -it vitalgraph-mongo mongosh -u vitaluser -p vitalpass \
  --authenticationDatabase admin vitalgraph --eval "db.device_metadata.find()"

# Neo4j browser: http://localhost:7474  (neo4j / vitalpass123)
```

## Ports

| Service | Port | Notes |
|---|---|---|
| Mosquitto | 1883 | anonymous access, local dev only |
| MySQL | 3306 | |
| MongoDB | 27018 | remapped — native mongod was already on 27017 on my machine |
| Neo4j browser | 7474 | http://localhost:7474 |
| Neo4j bolt | 7687 | |

## Layout

```
vitalgraph/
├── publisher/publisher.py     simulated wearables, publishes to MQTT
├── router/
│   ├── router.py               subscribe + dispatch + anomaly detection
│   ├── anomaly.py               threshold checks
│   └── dbclients/               MySQL/Mongo/Neo4j client wrappers
├── api/main.py                 FastAPI backend
├── dashboard_app.py             Streamlit dashboard
├── shared_constants.py         patient/device IDs, MQTT topics
├── db/
│   ├── mysql/init.sql
│   ├── mongo/seed.js
│   └── neo4j/seed.cypher, load_seed.sh
├── mosquitto/config/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── SPEC.md
```

## Requirements

- Docker + Docker Compose
- Python 3.11+
