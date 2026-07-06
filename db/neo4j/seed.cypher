CREATE (tigist:Patient {id: 'BKLTST85C54F158P', name: 'Tigist Bekele'});
CREATE (dawit:Patient  {id: 'HLADWT72S02F158E', name: 'Dawit Haile'});
CREATE (hiwot:Patient  {id: 'GRMHWT90L62F158Y', name: 'Hiwot Girma'});
CREATE (abdi:Patient   {id: 'BKLBDA88E19F158V', name: 'Abdi Bekele'});
CREATE (abinat:Patient {id: 'BRHBNT95P48F158M', name: 'Abinat Birhanu'});

CREATE (devA:Device {id: 'WXP-6305', type: 'smartwatch', model: 'Apple Watch Series 9'});
CREATE (devB:Device {id: 'CSE-3471', type: 'chest_strap', model: 'Polar H10'});
CREATE (devC:Device {id: 'WXL-7468', type: 'smartwatch', model: 'Fitbit Charge 6'});
CREATE (devD:Device {id: 'WXP-1791', type: 'smartwatch', model: 'Apple Watch Series 9'});
CREATE (devE:Device {id: 'WXL-2186', type: 'smartwatch', model: 'Fitbit Charge 6'});

CREATE (selam:Doctor    {id: 'MED-CARD-343', name: 'Dr. Selam Tadesse',  specialty: 'Cardiology',        on_duty: false});
CREATE (yonas:Doctor    {id: 'MED-CARD-706', name: 'Dr. Yonas Desta',    specialty: 'Cardiology',        on_duty: false});
CREATE (meron:Doctor    {id: 'MED-CARD-657', name: 'Dr. Meron Alemu',    specialty: 'General Medicine',  on_duty: true});
CREATE (melaku:Doctor   {id: 'MED-IMED-233', name: 'Dr. Melaku Tafesse', specialty: 'Internal Medicine', on_duty: true});
CREATE (siduna:Doctor   {id: 'MED-IMED-478', name: 'Dr. Siduna Girma',   specialty: 'Internal Medicine', on_duty: true});
CREATE (fikirte:Doctor  {id: 'MED-CARD-521', name: 'Dr. Fikirte Hailu',  specialty: 'Cardiology',        on_duty: true});

CREATE (teamCard:CareTeam {id: 'TEAM-CARD-A', name: 'Cardiology Team A'});
CREATE (teamIMed:CareTeam {id: 'TEAM-IMED-A', name: 'Internal Medicine Team A'});

MATCH (tigist:Patient  {id: 'BKLTST85C54F158P'}),
      (dawit:Patient   {id: 'HLADWT72S02F158E'}),
      (hiwot:Patient   {id: 'GRMHWT90L62F158Y'}),
      (abdi:Patient    {id: 'BKLBDA88E19F158V'}),
      (abinat:Patient  {id: 'BRHBNT95P48F158M'}),
      (devA:Device {id: 'WXP-6305'}),
      (devB:Device {id: 'CSE-3471'}),
      (devC:Device {id: 'WXL-7468'}),
      (devD:Device {id: 'WXP-1791'}),
      (devE:Device {id: 'WXL-2186'}),
      (selam:Doctor   {id: 'MED-CARD-343'}),
      (yonas:Doctor   {id: 'MED-CARD-706'}),
      (meron:Doctor   {id: 'MED-CARD-657'}),
      (melaku:Doctor  {id: 'MED-IMED-233'}),
      (siduna:Doctor  {id: 'MED-IMED-478'}),
      (fikirte:Doctor {id: 'MED-CARD-521'}),
      (teamCard:CareTeam {id: 'TEAM-CARD-A'}),
      (teamIMed:CareTeam {id: 'TEAM-IMED-A'})
CREATE (tigist)-[:OWNS]->(devA),
       (dawit)-[:OWNS]->(devB),
       (hiwot)-[:OWNS]->(devC),
       (abdi)-[:OWNS]->(devD),
       (abinat)-[:OWNS]->(devE),
       (tigist)-[:MONITORED_BY]->(selam),
       (dawit)-[:MONITORED_BY]->(yonas),
       (hiwot)-[:MONITORED_BY]->(meron),
       (abdi)-[:MONITORED_BY]->(melaku),
       (abinat)-[:MONITORED_BY]->(siduna),
       (selam)-[:MEMBER_OF]->(teamCard),
       (yonas)-[:MEMBER_OF]->(teamCard),
       (meron)-[:MEMBER_OF]->(teamCard),
       (melaku)-[:MEMBER_OF]->(teamIMed),
       (siduna)-[:MEMBER_OF]->(teamIMed),
       (fikirte)-[:MEMBER_OF]->(teamCard),
       (yonas)-[:BACKUP_FOR]->(selam),
       (fikirte)-[:BACKUP_FOR]->(yonas),
       (melaku)-[:BACKUP_FOR]->(meron),
       (siduna)-[:BACKUP_FOR]->(melaku);
