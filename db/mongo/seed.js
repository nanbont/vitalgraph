// VitalGraph: MongoDB seed
// device_metadata and symptom_logs are genuinely schema-varying data.
// alerts is the event-record collection populated at runtime by the router.
// See SPEC.md section 6 for rationale.

db = db.getSiblingDB("vitalgraph");

db.createCollection("device_metadata");
db.createCollection("symptom_logs");
db.createCollection("alerts");

db.device_metadata.insertMany([
  {
    _id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    model: "WearableX Pro",
    firmware_version: "2.3.1",
    battery_pct: 78,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps", "sleep"]
  },
  {
    _id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    model: "ChestStrap Elite",
    firmware_version: "1.8.0",
    battery_pct: 92,
    last_seen: new Date(),
    capabilities: ["heartrate"]
    // note: no steps/sleep/spo2 capability — chest straps don't track these.
    // this is the actual reason a fixed SQL column set would be awkward here.
  },
  {
    _id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    model: "WearableX Lite",
    firmware_version: "3.0.2",
    battery_pct: 65,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps"]
  }
]);

db.symptom_logs.insertMany([
  {
    patient_id: "11111111-1111-1111-1111-111111111111",
    reported_at: new Date(),
    text: "Felt dizzy after climbing stairs, lasted about 10 minutes",
    tags: ["dizziness"],
    severity_self_rated: 3
  },
  {
    patient_id: "22222222-2222-2222-2222-222222222222",
    reported_at: new Date(),
    text: "Mild headache in the afternoon"
    // note: no tags or severity rating — patient didn't fill those in.
    // optional fields like this are the point: no migrations needed.
  }
]);

print("VitalGraph MongoDB seed complete.");
