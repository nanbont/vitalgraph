#!/usr/bin/env bash
# VitalGraph: load the Neo4j seed.
# Neo4j's Docker image does not auto-execute .cypher files on init like
# MySQL/Mongo do, so this runs the seed manually via cypher-shell
# inside the running container. Run this once, after `docker compose up -d`.

set -e

NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-vitalpass123}"

echo "Waiting for Neo4j to be ready..."
until docker exec vitalgraph-neo4j cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" > /dev/null 2>&1; do
  sleep 2
done

echo "Loading seed data..."
docker exec vitalgraph-neo4j cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --file /seed/seed.cypher

echo "Neo4j seed loaded."
