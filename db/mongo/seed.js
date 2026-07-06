// VitalGraph MongoDB seed: device_metadata, symptom_logs, alerts.

db = db.getSiblingDB("vitalgraph");

db.createCollection("device_metadata");
db.createCollection("symptom_logs");
db.createCollection("alerts");

db.device_metadata.insertMany([
  {
    _id: "WXP-6305",
    model: "WearableX Pro",
    firmware_version: "2.3.1",
    battery_pct: 78,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps", "sleep"]
  },
  {
    _id: "CSE-3471",
    model: "ChestStrap Elite",
    firmware_version: "1.8.0",
    battery_pct: 92,
    last_seen: new Date(),
    capabilities: ["heartrate"]
    // chest straps only track heart rate
  },
  {
    _id: "WXL-7468",
    model: "WearableX Lite",
    firmware_version: "3.0.2",
    battery_pct: 65,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps"]
  },
  {
    _id: "WXP-1791",
    model: "WearableX Pro",
    firmware_version: "2.3.1",
    battery_pct: 88,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps", "sleep"]
  },
  {
    _id: "WXL-2186",
    model: "WearableX Lite",
    firmware_version: "3.0.2",
    battery_pct: 71,
    last_seen: new Date(),
    capabilities: ["heartrate", "spo2", "steps"]
  }
]);

db.symptom_logs.insertMany([
  {
    patient_id: "RMNLCA85C54F158S",
    reported_at: new Date(),
    text: "Felt dizzy after climbing stairs, lasted about 10 minutes",
    tags: ["dizziness"],
    severity_self_rated: 3
  },
  {
    patient_id: "BLLMRC72S02F158W",
    reported_at: new Date(),
    text: "Mild headache in the afternoon"
    // optional fields, not filled in here
  }
]);

db.alerts.createIndex(
  { detected_at: 1 },
  { expireAfterSeconds: 2592000, name: "ttl_alerts_30days" }
);

print("VitalGraph MongoDB seed complete.");
