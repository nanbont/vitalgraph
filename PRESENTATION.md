cd ~/vitalgraph
source .venv/bin/activate
docker compose up -d
docker compose ps

# if neo4j volume is fresh, seed once (don't run twice without wiping volume first)
./db/neo4j/load_seed.sh

# terminal 1
python router/router.py

# terminal 2
python publisher/publisher.py

# terminal 3
streamlit run dashboard_app.py
# localhost:8501

# escalation query, run manually
docker exec -it vitalgraph-neo4j cypher-shell -u neo4j -p vitalpass123 "MATCH (p:Patient {id: 'RMNLCA85C54F158S'})-[:MONITORED_BY]->(primary:Doctor) OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary) RETURN primary.name AS primary_doctor, primary.on_duty AS primary_on_duty, coalesce(available.name, primary.name) AS notified, length(path) AS chain_depth ORDER BY chain_depth LIMIT 1;"

# if neo4j has duplicates (count should be 17)
docker exec -it vitalgraph-neo4j cypher-shell -u neo4j -p vitalpass123 "MATCH (n) RETURN count(n);"
docker compose rm -sf neo4j
docker volume rm vitalgraph_neo4j-data
docker compose up -d neo4j
./db/neo4j/load_seed.sh

# check router/publisher still running
ps aux | grep -E "router.py|publisher.py"
