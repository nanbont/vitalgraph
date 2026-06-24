// VitalGraph: Neo4j seed
// Care network only — Patients, Doctors, CareTeams, escalation chains.
// No Alert nodes: alerts are event records and live in MongoDB.
// See SPEC.md section 7 for rationale and query patterns.

// Patients (ids match the MySQL seed exactly)
CREATE (alice:Patient {id: '11111111-1111-1111-1111-111111111111', name: 'Alice Romano'});
CREATE (marco:Patient {id: '22222222-2222-2222-2222-222222222222', name: 'Marco Bellini'});
CREATE (sara:Patient  {id: '33333333-3333-3333-3333-333333333333', name: 'Sara Conti'});

// Devices (lightweight nodes, ids match MySQL/Mongo — used for correlation queries only)
CREATE (devA:Device {id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', type: 'smartwatch'});
CREATE (devB:Device {id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', type: 'chest_strap'});
CREATE (devC:Device {id: 'cccccccc-cccc-cccc-cccc-cccccccccccc', type: 'smartwatch'});

// Doctors
CREATE (drRossi:Doctor {id: 'd1111111-0000-0000-0000-000000000001', name: 'Dr. Rossi', specialty: 'Cardiology', on_duty: true});
CREATE (drBianchi:Doctor {id: 'd2222222-0000-0000-0000-000000000002', name: 'Dr. Bianchi', specialty: 'Cardiology', on_duty: false});
CREATE (drVerdi:Doctor {id: 'd3333333-0000-0000-0000-000000000003', name: 'Dr. Verdi', specialty: 'General Medicine', on_duty: true});

// Care team
CREATE (team:CareTeam {id: 't1111111-0000-0000-0000-000000000001', name: 'Cardiology Team A'});

// Relationships
MATCH (alice:Patient {id: '11111111-1111-1111-1111-111111111111'}),
      (marco:Patient {id: '22222222-2222-2222-2222-222222222222'}),
      (sara:Patient  {id: '33333333-3333-3333-3333-333333333333'}),
      (devA:Device {id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'}),
      (devB:Device {id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'}),
      (devC:Device {id: 'cccccccc-cccc-cccc-cccc-cccccccccccc'}),
      (drRossi:Doctor {id: 'd1111111-0000-0000-0000-000000000001'}),
      (drBianchi:Doctor {id: 'd2222222-0000-0000-0000-000000000002'}),
      (drVerdi:Doctor {id: 'd3333333-0000-0000-0000-000000000003'}),
      (team:CareTeam {id: 't1111111-0000-0000-0000-000000000001'})
CREATE (alice)-[:OWNS]->(devA),
       (marco)-[:OWNS]->(devB),
       (sara)-[:OWNS]->(devC),
       (alice)-[:MONITORED_BY]->(drBianchi),   // Bianchi is OFF duty -> escalation chain matters
       (marco)-[:MONITORED_BY]->(drRossi),
       (sara)-[:MONITORED_BY]->(drVerdi),
       (drRossi)-[:MEMBER_OF]->(team),
       (drBianchi)-[:MEMBER_OF]->(team),
       (drRossi)-[:BACKUP_FOR]->(drBianchi);   // Rossi covers for Bianchi when Bianchi is off duty
       // Semantics: (X)-[:BACKUP_FOR]->(Y) means "X is the backup for Y".
       // So to find who covers for a given doctor D, walk: (covering)-[:BACKUP_FOR]->(D)
       // i.e. traverse the relationship BACKWARDS from the primary doctor.

// Sanity check query (run manually to verify the seed):
// MATCH (p:Patient {id: '11111111-1111-1111-1111-111111111111'})-[:MONITORED_BY]->(primary:Doctor)
// OPTIONAL MATCH path = (available:Doctor {on_duty: true})-[:BACKUP_FOR*0..3]->(primary)
// RETURN coalesce(available, primary) AS notify, length(path) AS chain_depth
// ORDER BY chain_depth LIMIT 1;
