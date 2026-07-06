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
    ('BKLTST85C54F158P', 'Tigist Bekele', '1985-03-14'),
    ('HLADWT72S02F158E', 'Dawit Haile', '1972-11-02'),
    ('GRMHWT90L62F158Y', 'Hiwot Girma', '1990-07-22'),
    ('BKLBDA88E19F158V', 'Abdi Bekele', '1988-05-19'),
    ('BRHBNT95P48F158M', 'Abinat Birhanu', '1995-09-08');

INSERT INTO devices (device_id, patient_id, device_type) VALUES
    ('WXP-6305', 'BKLTST85C54F158P', 'Apple Watch Series 9'),
    ('CSE-3471', 'HLADWT72S02F158E', 'Polar H10'),
    ('WXL-7468', 'GRMHWT90L62F158Y', 'Fitbit Charge 6'),
    ('WXP-1791', 'BKLBDA88E19F158V', 'Apple Watch Series 9'),
    ('WXL-2186', 'BRHBNT95P48F158M', 'Fitbit Charge 6');

CREATE TABLE anomaly_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_id CHAR(36) NOT NULL,
    device_id CHAR(36) NOT NULL,
    reading_type VARCHAR(20) NOT NULL,
    value DECIMAL(6,1) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    threshold DECIMAL(6,1) NOT NULL,
    logged_at DATETIME DEFAULT (UTC_TIMESTAMP()),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

DELIMITER //
CREATE TRIGGER trg_heartrate_anomaly
AFTER INSERT ON vitals_heartrate
FOR EACH ROW
BEGIN
    IF NEW.bpm > 140 THEN
        INSERT INTO anomaly_log (patient_id, device_id, reading_type, value, direction, threshold)
        VALUES (NEW.patient_id, NEW.device_id, 'heartrate', NEW.bpm, 'high', 140);
    ELSEIF NEW.bpm < 40 THEN
        INSERT INTO anomaly_log (patient_id, device_id, reading_type, value, direction, threshold)
        VALUES (NEW.patient_id, NEW.device_id, 'heartrate', NEW.bpm, 'low', 40);
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER trg_spo2_anomaly
AFTER INSERT ON vitals_spo2
FOR EACH ROW
BEGIN
    IF NEW.spo2_pct < 92 THEN
        INSERT INTO anomaly_log (patient_id, device_id, reading_type, value, direction, threshold)
        VALUES (NEW.patient_id, NEW.device_id, 'spo2', NEW.spo2_pct, 'low', 92);
    END IF;
END//
DELIMITER ;

CREATE VIEW patient_vitals_summary AS
SELECT 
    p.patient_id,
    p.name,
    p.date_of_birth,
    hr.bpm AS latest_bpm,
    hr.recorded_at AS latest_hr_time,
    s.spo2_pct AS latest_spo2,
    s.recorded_at AS latest_spo2_time,
    COUNT(a.id) AS total_anomalies
FROM patients p
LEFT JOIN vitals_heartrate hr ON hr.patient_id = p.patient_id
    AND hr.recorded_at = (
        SELECT MAX(recorded_at) FROM vitals_heartrate 
        WHERE patient_id = p.patient_id
    )
LEFT JOIN vitals_spo2 s ON s.patient_id = p.patient_id
    AND s.recorded_at = (
        SELECT MAX(recorded_at) FROM vitals_spo2 
        WHERE patient_id = p.patient_id
    )
LEFT JOIN anomaly_log a ON a.patient_id = p.patient_id
GROUP BY p.patient_id, p.name, p.date_of_birth, hr.bpm, hr.recorded_at, s.spo2_pct, s.recorded_at;

DELIMITER //
CREATE PROCEDURE get_patient_summary(IN p_id CHAR(36))
BEGIN
    SELECT 
        p.name,
        p.date_of_birth,
        hr.bpm AS latest_bpm,
        hr.recorded_at AS latest_hr_time,
        s.spo2_pct AS latest_spo2
    FROM patients p
    LEFT JOIN vitals_heartrate hr ON hr.patient_id = p.patient_id
        AND hr.recorded_at = (SELECT MAX(recorded_at) FROM vitals_heartrate WHERE patient_id = p_id)
    LEFT JOIN vitals_spo2 s ON s.patient_id = p.patient_id
        AND s.recorded_at = (SELECT MAX(recorded_at) FROM vitals_spo2 WHERE patient_id = p_id)
    WHERE p.patient_id = p_id;

    SELECT reading_type, value, direction, threshold, logged_at
    FROM anomaly_log
    WHERE patient_id = p_id
    ORDER BY logged_at DESC
    LIMIT 5;
END//
DELIMITER ;
