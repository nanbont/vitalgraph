// VitalGraph Neo4j seed: care network only, no Alert nodes (those live in MongoDB).

// Patients
CREATE (alice:Patient {id: 'RMNLCA85C54F158S', name: 'Alice Romano'});
CREATE (marco:Patient {id: 'BLLMRC72S02F158W', name: 'Marco Bellini'});
CREATE (sara:Patient  {id: 'CNTSRA90L62F158K', name: 'Sara Conti'});
CREATE (abdi:Patient  {id: 'BKLBDA88E19F158V', name: 'Abdi Bekele'});
CREATE (abinat:Patient {id: 'BRHBNT95P48F158M', name: 'Abinat Birhanu'});

// Devices (for correlation queries only)
CREATE (devA:Device {id: 'WXP-6305', type: 'smartwatch'});
CREATE (devB:Device {id: 'CSE-3471', type: 'chest_strap'});
CREATE (devC:Device {id: 'WXL-7468', type: 'smartwatch'});
CREATE (devD:Device {id: 'WXP-1791', type: 'smartwatch'});
CREATE (devE:Device {id: 'WXL-2186', type: 'smartwatch'});

// Doctors
CREATE (drRossi:Doctor   {id: 'MED-CARD-706', name: 'Dr. Rossi', specialty: 'Cardiology', on_duty: true});
CREATE (drBianchi:Doctor {id: 'MED-CARD-343', name: 'Dr. Bianchi', specialty: 'Cardiology', on_duty: false});
CREATE (drVerdi:Doctor   {id: 'MED-CARD-657', name: 'Dr. Verdi', specialty: 'General Medicine', on_duty: true});
CREATE (drMelaku:Doctor  {id: 'MED-IMED-233', name: 'Dr. Melaku Tafesse', specialty: 'Internal Medicine', on_duty: true});
CREATE (drSiduna:Doctor  {id: 'MED-IMED-478', name: 'Dr. Siduna Girma', specialty: 'Internal Medicine', on_duty: true});

// Care teams
CREATE (teamCard:CareTeam {id: 'TEAM-CARD-A', name: 'Cardiology Team A'});
CREATE (teamIMed:CareTeam {id: 'TEAM-IMED-A', name: 'Internal Medicine Team A'});

// Relationships
MATCH (alice:Patient {id: 'RMNLCA85C54F158S'}),
      (marco:Patient {id: 'BLLMRC72S02F158W'}),
      (sara:Patient  {id: 'CNTSRA90L62F158K'}),
      (abdi:Patient  {id: 'BKLBDA88E19F158V'}),
      (abinat:Patient {id: 'BRHBNT95P48F158M'}),
      (devA:Device {id: 'WXP-6305'}),
      (devB:Device {id: 'CSE-3471'}),
      (devC:Device {id: 'WXL-7468'}),
      (devD:Device {id: 'WXP-1791'}),
      (devE:Device {id: 'WXL-2186'}),
      (drRossi:Doctor {id: 'MED-CARD-706'}),
      (drBianchi:Doctor {id: 'MED-CARD-343'}),
      (drVerdi:Doctor {id: 'MED-CARD-657'}),
      (drMelaku:Doctor {id: 'MED-IMED-233'}),
      (drSiduna:Doctor {id: 'MED-IMED-478'}),
      (teamCard:CareTeam {id: 'TEAM-CARD-A'}),
      (teamIMed:CareTeam {id: 'TEAM-IMED-A'})
CREATE (alice)-[:OWNS]->(devA),
       (marco)-[:OWNS]->(devB),
       (sara)-[:OWNS]->(devC),
       (abdi)-[:OWNS]->(devD),
       (abinat)-[:OWNS]->(devE),

       (alice)-[:MONITORED_BY]->(drBianchi),   // Bianchi is OFF duty -> escalation chain matters
       (marco)-[:MONITORED_BY]->(drRossi),
       (sara)-[:MONITORED_BY]->(drVerdi),
       (abdi)-[:MONITORED_BY]->(drMelaku),
       (abinat)-[:MONITORED_BY]->(drSiduna),

       (drRossi)-[:MEMBER_OF]->(teamCard),
       (drBianchi)-[:MEMBER_OF]->(teamCard),
       (drVerdi)-[:MEMBER_OF]->(teamCard),
       (drMelaku)-[:MEMBER_OF]->(teamIMed),
       (drSiduna)-[:MEMBER_OF]->(teamIMed),

       (drRossi)-[:BACKUP_FOR]->(drBianchi),    // Rossi covers for Bianchi when Bianchi is off duty
       (drMelaku)-[:BACKUP_FOR]->(drVerdi),      // Melaku covers for Verdi
       (drSiduna)-[:BACKUP_FOR]->(drMelaku);     // Siduna covers for Melaku
       // (X)-[:BACKUP_FOR]->(Y) = "X is the backup for Y" — traverse
       // BACKWARDS from the primary doctor to find who covers for them.

// Sanity check: see the escalation query in api/ or SPEC.md section 7.
