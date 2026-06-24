"""
VitalGraph Router: Neo4j escalation queries.

The graph is queried AT ALERT TIME to decide who to notify — it is not
written to as an event log. See SPEC.md section 3 and 7 for the full
rationale on why this keeps the graph's role honest (relationships, not
records).
"""

import os

from neo4j import GraphDatabase


def get_driver():
    uri = f"bolt://{os.environ.get('NEO4J_HOST', 'localhost')}:{os.environ.get('NEO4J_BOLT_PORT', 7687)}"
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "vitalpass123")
    return GraphDatabase.driver(uri, auth=(user, password))


# See SPEC.md section 7, Query 1. Semantics reminder: (X)-[:BACKUP_FOR]->(Y)
# means "X is the backup for Y", so we walk BACKWARDS from the primary
# doctor to find a covering, on-duty doctor.
ESCALATION_QUERY = """
MATCH (p:Patient {id: $patientId})-[:MONITORED_BY]->(primary:Doctor)
OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
WITH primary, available, path
ORDER BY length(path)
LIMIT 1
RETURN coalesce(available, primary) AS notify, primary.name AS primary_name
"""


def resolve_notified_doctor(driver, patient_id: str) -> dict | None:
    """
    Returns {"doctor_id": ..., "doctor_name": ..., "primary_doctor_name": ...}
    or None if the patient has no monitoring doctor (shouldn't happen with
    seeded data, but the router should handle it gracefully rather than crash).
    """
    with driver.session() as session:
        result = session.run(ESCALATION_QUERY, patientId=patient_id)
        record = result.single()
        if record is None or record["notify"] is None:
            return None
        notify_node = record["notify"]
        return {
            "doctor_id": notify_node["id"],
            "doctor_name": notify_node["name"],
            "primary_doctor_name": record["primary_name"],
        }


# See SPEC.md section 7, Query 3 — analytical correlation, not used in the
# real-time alert path. Exposed here for the API/dashboard layer.
DEVICE_CORRELATION_QUERY = """
MATCH (p1:Patient)-[:OWNS]->(d1:Device)
MATCH (p2:Patient)-[:OWNS]->(d2:Device)
WHERE d1.type = d2.type AND p1.id < p2.id
RETURN p1.name AS patient_a, p2.name AS patient_b, d1.type AS device_type
"""


def device_sharing_pairs(driver) -> list[dict]:
    with driver.session() as session:
        result = session.run(DEVICE_CORRELATION_QUERY)
        return [dict(record) for record in result]
