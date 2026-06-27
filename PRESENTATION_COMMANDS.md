# Demo commands

Run in this order. Three terminals needed (router, publisher, dashboard).

## 1. Start the stack

```bash
docker compose up -d
```
brings up MySQL, MongoDB, Neo4j, and Mosquitto

```bash
docker ps
```
confirms all four containers are Up before continuing

## 2. Activate the environment

```bash
source .venv/bin/activate
```

## 3. Terminal 1 — router

```bash
python router/router.py
```
subscribes to MQTT, waits for messages, runs the escalation query when an anomaly fires

## 4. Terminal 2 — publisher

```bash
python publisher/publisher.py
```
simulates five wearables sending vitals every 10-30 seconds, for 50 rounds

## 5. Terminal 3 — dashboard

```bash
streamlit run dashboard_app.py
```
opens at http://localhost:8501, reads MySQL/MongoDB/Neo4j directly

## 6. (optional) FastAPI backend

```bash
uvicorn api.main:app --reload --port 8000
```
REST/WebSocket access independent of the dashboard, not required for the demo

## 7. (optional) Run the escalation query manually

Open http://localhost:7474 (neo4j / vitalpass123), then:

```cypher
MATCH (p:Patient {id: $patientId})-[:MONITORED_BY]->(primary:Doctor)
OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
RETURN coalesce(available, primary) AS notify, length(path) AS chain_depth
ORDER BY chain_depth
LIMIT 1;
```
get a real patient_id from the MySQL patients table or a router ALERT log line first

## Cleanup

```bash
docker compose down
```
