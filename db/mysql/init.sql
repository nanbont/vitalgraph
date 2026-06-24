-- VitalGraph: MySQL schema
-- Structured, high-frequency vitals time-series. See SPEC.md section 5 for rationale.
--
-- All timestamps are stored as UTC DATETIME. MySQL's timezone handling is
-- less explicit than Postgres's TIMESTAMPTZ, so the application layer is
-- responsible for converting to/from UTC consistently — there is no
-- column-level timezone awareness here.
--
-- Note on rolling averages: MySQL 8's window functions support
-- ROWS BETWEEN but not Postgres-style RANGE BETWEEN INTERVAL (time-based
-- windows). Rolling averages over a time window are computed in the
-- Python API layer instead of in SQL. See router/ and api/ once written.

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

-- Seed: a handful of demo patients + devices so the dashboard has data on day 1.
-- IDs are fixed (not random) so they match the Mongo and Neo4j seeds exactly.

INSERT INTO patients (patient_id, name, date_of_birth) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Alice Romano', '1985-03-14'),
    ('22222222-2222-2222-2222-222222222222', 'Marco Bellini', '1972-11-02'),
    ('33333333-3333-3333-3333-333333333333', 'Sara Conti', '1990-07-22');

INSERT INTO devices (device_id, patient_id, device_type) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'smartwatch'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 'chest_strap'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', '33333333-3333-3333-3333-333333333333', 'smartwatch');
