# VitalGraph

Polyglot health-monitoring platform: simulated wearables stream vitals over
MQTT, a Python router persists them across MySQL, MongoDB, and Neo4j —
each chosen because it genuinely fits a different part of the data, not as
a forced tour of three databases. See [`SPEC.md`](./SPEC.md) for the full
design rationale, schemas, and query patterns.

## Status

Infrastructure is up: Mosquitto, MySQL, MongoDB, and Neo4j, all seeded
with demo patients/doctors/devices so the data model can be inspected before
any application code is written. Publisher, router, API, and dashboard are
the next build phase.

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
| MongoDB | 27017 | |
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | used by the Python driver |

## Repo structure

```
vitalgraph/
├── publisher/            # (next) simulator publishing fake vitals to MQTT
├── router/                # (next) subscriber + dispatch + anomaly detection
├── api/                    # (next) FastAPI app
├── dashboard/              # (next) frontend
├── db/
│   ├── mysql/init.sql
│   ├── mongo/seed.js
│   └── neo4j/seed.cypher, load_seed.sh
├── mosquitto/config/
├── docker-compose.yml
├── .env.example
├── SPEC.md
└── README.md
```
