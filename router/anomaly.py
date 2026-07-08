"""Heart rate / SpO2 threshold checks."""
from shared_constants import HR_HIGH_THRESHOLD, HR_LOW_THRESHOLD, SPO2_LOW_THRESHOLD

def check_heartrate(bpm: int) -> dict | None:
    if bpm > HR_HIGH_THRESHOLD:
        severity = "high" if bpm > 160 else "warning"
        return {
            "alert_type": "abnormal_heartrate",
            "severity": severity,
            "detail": {"bpm": bpm, "threshold": HR_HIGH_THRESHOLD, "direction": "high"},
        }
    if bpm < HR_LOW_THRESHOLD:
        return {
            "alert_type": "abnormal_heartrate",
            "severity": "high",
            "detail": {"bpm": bpm, "threshold": HR_LOW_THRESHOLD, "direction": "low"},
        }
    return None

def check_spo2(spo2_pct: float) -> dict | None:
    if spo2_pct < SPO2_LOW_THRESHOLD:
        severity = "high" if spo2_pct < 85 else "warning"
        return {
            "alert_type": "low_spo2",
            "severity": severity,
            "detail": {"spo2_pct": spo2_pct, "threshold": SPO2_LOW_THRESHOLD},
        }
    return None
