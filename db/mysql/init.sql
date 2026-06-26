-- VitalGraph MySQL schema. Rolling averages computed in Python (see api/), not SQL.

CREATE TABLE patients (
    patient_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    created_at DATETIME DEFAULT (UTC_TIMESTAMP())
);

CREATE TABLE devices (
    device_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    patient_id CHAR(36),
    device_type VARCHAR(100) NOT NULL,   -- 'smartwatch', 'chest_strap', etc.
    registered_at DATETIME DEFAULT (UTC_TIMESTAMP()),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE vitals_heartrate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    bpm INT NOT NULL,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_hr_patient_time ON vitals_heartrate (patient_id, recorded_at DESC);

CREATE TABLE vitals_spo2 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    spo2_pct DECIMAL(4,1) NOT NULL,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_spo2_patient_time ON vitals_spo2 (patient_id, recorded_at DESC);

CREATE TABLE vitals_activity (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36),
    device_id CHAR(36),
    steps INT,
    sleep_minutes INT,
    recorded_at DATETIME NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_activity_patient_time ON vitals_activity (patient_id, recorded_at DESC);

-- Seed data: 5 demo patients + devices. IDs match the Mongo/Neo4j seeds.

INSERT INTO patients (patient_id, name, date_of_birth) VALUES
    ('RMNLCA85C54F158S', 'Alice Romano', '1985-03-14'),
    ('BLLMRC72S02F158W', 'Marco Bellini', '1972-11-02'),
    ('CNTSRA90L62F158K', 'Sara Conti', '1990-07-22'),
    ('BKLBDA88E19F158V', 'Abdi Bekele', '1988-05-19'),
    ('BRHBNT95P48F158M', 'Abinat Birhanu', '1995-09-08');

INSERT INTO devices (device_id, patient_id, device_type) VALUES
    ('WXP-6305', 'RMNLCA85C54F158S', 'smartwatch'),
    ('CSE-3471', 'BLLMRC72S02F158W', 'chest_strap'),
    ('WXL-7468', 'CNTSRA90L62F158K', 'smartwatch'),
    ('WXP-1791', 'BKLBDA88E19F158V', 'smartwatch'),
    ('WXL-2186', 'BRHBNT95P48F158M', 'smartwatch');
