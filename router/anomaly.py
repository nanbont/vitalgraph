"""
VitalGraph Router: anomaly detection.

Simple threshold checks, run immediately after a vitals write to MySQL.
See SPEC.md section 8 for rationale (kept simple and explainable, not a
black-box ML model — appropriate for the scope of this assignment).
"""

from shared_constants import HR_HIGH_THRESHOLD, HR_LOW_THRESHOLD, SPO2_LOW_THRESHOLD


def check_heartrate(bpm: int) -> dict | None:
    if bpm > HR_HIGH_THRESHOLD:
        return {
            "alert_type": "abnormal_heartrate",
            "severity": "high",
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
        return {
            "alert_type": "low_spo2",
            "severity": "high",
            "detail": {"spo2_pct": spo2_pct, "threshold": SPO2_LOW_THRESHOLD},
        }
    return None
