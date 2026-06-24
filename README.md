# VitalGraph

Polyglot health-monitoring platform: simulated wearables stream vitals over
MQTT, a Python router persists them across MySQL, MongoDB, and Neo4j —
each chosen because it genuinely fits a different part of the data, not as
a forced tour of three databases. See [`SPEC.md`](./SPEC.md) for the full
design rationale, schemas, and query patterns.

## Status

Infrastructure (Mosquitto, MySQL, MongoDB, Neo4j) is up and seeded.
Publisher (wearable simulator) and Router (MQTT subscriber + anomaly
detection + Neo4j escalation) are implemented and tested. FastAPI and the
dashboard are the next build phase.

## Running the publisher and router

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1
python router/router.py

# Terminal 2
python publisher/publisher.py
```

The router logs every message it processes; when an anomalous reading
fires, you'll see an `ALERT` line showing which doctor was resolved via
the Neo4j escalation query (see `SPEC.md` section 7).

## Prerequisites

- Docker + Docker Compose
- (Later, for app code) Python 3.11+

## Getting started

```bash
cp .env.example .env

docker compose up -d

# MySQL and Mongo seed automatically on first start.
# Neo4j needs its seed loaded manually (see note below):
./db/neo4j/load_seed.sh
```

### Why Neo4j needs a manual step

MySQL and Mongo's official images auto-run init scripts mounted into
their entrypoint directories. Neo4j's image doesn't support this for
`.cypher` files, so `load_seed.sh` waits for the container to be healthy
and runs the seed via `cypher-shell` directly.

## Verifying the environment

```bash
docker ps
# expect: vitalgraph-mosquitto, vitalgraph-mysql, vitalgraph-mongo, vitalgraph-neo4j

# MySQL
docker exec -it vitalgraph-mysql mysql -u vitaluser -pvitalpass vitalgraph -e "SELECT * FROM patients;"

# Mongo
docker exec -it vitalgraph-mongo mongosh -u vitaluser -p vitalpass --authenticationDatabase admin vitalgraph --eval "db.device_metadata.find()"

# Neo4j browser UI
# open http://localhost:7474  (user: neo4j / password: vitalpass123)
```

## Service ports

| Service | Port | Notes |
|---|---|---|
| Mosquitto (MQTT) | 1883 | anonymous access allowed — local dev only, see note in `mosquitto/config/mosquitto.conf` |
| MySQL | 3306 | |
| MongoDB | 27018 | remapped from default 27017 — a native mongod is already using that port on this machine |
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | used by the Python driver |

## Repo structure

```
vitalgraph/
├── publisher/
│   └── publisher.py        # wearable simulator, publishes to MQTT
├── router/
│   ├── router.py            # subscriber + dispatch + anomaly detection
│   ├── anomaly.py            # threshold checks
│   └── db/
│       ├── mysql_client.py
│       ├── mongo_client.py
│       └── neo4j_client.py
├── shared_constants.py      # patient/device IDs + MQTT topics, shared by publisher & router
├── api/                       # (next) FastAPI app
├── dashboard/                 # (next) frontend
├── db/
│   ├── mysql/init.sql
│   ├── mongo/seed.js
│   └── neo4j/seed.cypher, load_seed.sh
├── mosquitto/config/
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── SPEC.md
└── README.md
```
