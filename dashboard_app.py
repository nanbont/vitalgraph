"""VitalGraph dashboard. Run: streamlit run dashboard_app.py"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "router"))
load_dotenv(ROOT / ".env")

from dbclients import mongo_client, mysql_client, neo4j_client  # noqa: E402
from shared_constants import PATIENTS  # noqa: E402

sys.path.append(str(ROOT / "api"))
from rolling_average import with_rolling_average  # noqa: E402

st.set_page_config(page_title="VitalGraph", page_icon="🩺", layout="wide")

INK = "#1C2B33"
PAPER = "#FAFAF8"
PANEL = "#FFFFFF"
HAIRLINE = "#E3E0D8"
TEAL = "#2C6E63"
TEAL_SOFT = "#E9F2EF"
RED = "#C84B31"
RED_SOFT = "#FBEAE6"
AMBER = "#C68A1E"
MUTED = "#6B7680"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; color: {INK}; }}
.stApp {{ background-color: {PAPER}; }}
section[data-testid="stSidebar"] {{ background-color: {PANEL}; border-right: 1px solid {HAIRLINE}; }}
h1, h2, h3, h4, h5 {{ font-family: 'Source Serif 4', serif; color: {INK}; letter-spacing: -0.01em; }}
.vg-eyebrow {{ font-family: 'IBM Plex Sans', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: {MUTED}; margin-bottom: 0.15rem; }}
.vg-brand {{ font-family: 'Source Serif 4', serif; font-weight: 700; font-size: 1.5rem; color: {INK}; margin: 0; }}
.vg-brand-sub {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: {MUTED}; margin-top: 0.1rem; }}
hr, [data-testid="stDivider"] {{ border-color: {HAIRLINE} !important; }}
.vg-strip {{ background: {PANEL}; border: 1px solid {HAIRLINE}; border-left: 5px solid {TEAL}; border-radius: 4px; padding: 1.1rem 1.4rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; }}
.vg-strip.escalated {{ border-left-color: {RED}; background: {RED_SOFT}; }}
.vg-strip.stable {{ border-left-color: {TEAL}; background: {TEAL_SOFT}; }}
.vg-strip-name {{ font-family: 'Source Serif 4', serif; font-size: 1.4rem; font-weight: 600; color: {INK}; }}
.vg-strip-meta {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: {MUTED}; }}
.vg-status-pill {{ font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 0.85rem; padding: 0.45rem 0.9rem; border-radius: 20px; white-space: nowrap; }}
.vg-status-pill.escalated {{ background: {RED}; color: white; }}
.vg-status-pill.stable {{ background: {TEAL}; color: white; }}
.vg-section-label {{ font-family: 'IBM Plex Sans', sans-serif; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: {MUTED}; border-bottom: 1px solid {HAIRLINE}; padding-bottom: 0.4rem; margin-bottom: 0.8rem; }}
.vg-alert {{ background: {PANEL}; border: 1px solid {HAIRLINE}; border-left: 4px solid {RED}; border-radius: 4px; padding: 0.8rem 1rem; margin-bottom: 0.7rem; }}
.vg-alert.amber {{ border-left-color: {AMBER}; }}
.vg-alert-title {{ font-weight: 600; font-size: 0.95rem; color: {INK}; }}
.vg-alert-meta {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.74rem; color: {MUTED}; margin-top: 0.2rem; }}
.vg-alert-notify {{ font-size: 0.85rem; margin-top: 0.4rem; color: {INK}; }}
.vg-alert-notify b {{ color: {TEAL}; }}
.vg-oncall-card {{ background: {TEAL_SOFT}; border: 1px solid {HAIRLINE}; border-left: 4px solid {TEAL}; border-radius: 4px; padding: 0.6rem 0.9rem; margin-bottom: 0.5rem; }}
.vg-oncall-name {{ font-weight: 600; font-size: 0.9rem; color: {INK}; }}
.vg-oncall-meta {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: {MUTED}; }}
.vg-stat-card {{ background: {PANEL}; border: 1px solid {HAIRLINE}; border-radius: 4px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; }}
.vg-stat-name {{ font-weight: 600; font-size: 0.9rem; color: {INK}; }}
.vg-stat-numbers {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.74rem; color: {MUTED}; margin-top: 0.2rem; }}
[data-testid="stMetricValue"] {{ font-family: 'Source Serif 4', serif; color: {INK}; }}
[data-testid="stMetricLabel"] {{ font-family: 'IBM Plex Sans', sans-serif; color: {MUTED}; }}
.stTabs [data-baseweb="tab"] {{ font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; }}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_connections():
    return {
        "mysql": mysql_client.get_connection(),
        "mongo_db": mongo_client.get_db(mongo_client.get_client()),
        "neo4j": neo4j_client.get_driver(),
    }


conn = get_connections()

def get_mysql():
    db = conn["mysql"]
    try:
        db.ping(reconnect=True)
    except Exception:
        get_connections.clear()
        conn_new = get_connections()
        return conn_new["mysql"]
    return db


def short_id(full_id: str) -> str:
    return full_id.split("-")[0]


def vitals_chart(df, value_col, value_label, color):
    melted = df.melt(id_vars=["recorded_at"], value_vars=[value_col, "rolling_avg"], var_name="series", value_name="value")
    melted["series"] = melted["series"].map({value_col: value_label, "rolling_avg": "10-min avg"})
    chart = (
        alt.Chart(melted).mark_line().encode(
            x=alt.X("recorded_at:T", title="Time"),
            y=alt.Y("value:Q", title=value_label, scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None, scale=alt.Scale(domain=[value_label, "10-min avg"], range=[color, MUTED])),
            strokeDash=alt.condition(alt.datum.series == "10-min avg", alt.value([4, 3]), alt.value([1, 0])),
        )
        .configure_axis(labelFont="IBM Plex Mono", titleFont="IBM Plex Sans", grid=False)
        .configure_view(strokeWidth=0)
        .properties(height=210)
    )
    st.altair_chart(chart, use_container_width=True)


# ── SIDEBAR ──────────────────────────────────────────────────────────
patients = mysql_client.fetch_all_patients(get_mysql())
patient_names = {p["patient_id"]: p["name"] for p in patients}

with st.sidebar:
    st.markdown('<p class="vg-brand">🩺 VitalGraph</p><p class="vg-brand-sub">MQTT · MYSQL · MONGODB · NEO4J</p>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<p class="vg-eyebrow">Patient</p>', unsafe_allow_html=True)
    selected_id = st.radio("Patient", options=list(patient_names.keys()), format_func=lambda pid: patient_names[pid], label_visibility="collapsed")
    st.divider()
    st.divider()
    st.markdown("**Patients — MySQL**")
    df_patients = pd.DataFrame(patients)[["patient_id", "name", "date_of_birth"]]
    df_patients["date_of_birth"] = pd.to_datetime(df_patients["date_of_birth"]).dt.strftime("%Y-%m-%d")
    df_patients["device"] = df_patients["patient_id"].apply(lambda pid: PATIENTS.get(pid, {}).get("device_type", ""))
    df_patients = df_patients[["name", "date_of_birth", "device"]]
    df_patients = df_patients.rename(columns={"name": "Name", "date_of_birth": "DOB", "device": "Device"})
    st.dataframe(df_patients, use_container_width=True, hide_index=True, column_config={
        "Name": st.column_config.TextColumn(width="small"),
        "DOB": st.column_config.TextColumn(width="small"),
        "Device": st.column_config.TextColumn(width="medium"),
    })


# ── TOP: CARE NETWORK BANNER ─────────────────────────────────────────
resolution = neo4j_client.resolve_notified_doctor(conn["neo4j"], selected_id)
if resolution:
    escalated = resolution["doctor_name"] != resolution["primary_doctor_name"]
    state_class = "escalated" if escalated else "stable"
    status_text = f"Escalated to {resolution['doctor_name']}" if escalated else f"On duty — {resolution['doctor_name']} notified directly"
    st.markdown(f"""
        <div class="vg-strip {state_class}">
            <div>
                <div class="vg-eyebrow">Care network · Neo4j</div>
                <div class="vg-strip-name">{patient_names[selected_id]}</div>
                <div class="vg-strip-meta">PRIMARY: {resolution['primary_doctor_name'].upper()}</div>
            </div>
            <div class="vg-status-pill {state_class}">{status_text}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.warning("No care network found for this patient.")

st.write("")

# ── PATIENT SUMMARY METRICS (MySQL view) ─────────────────────────────
try:
    cur = get_mysql().cursor(dictionary=True)
    cur.execute("SELECT * FROM patient_vitals_summary WHERE patient_id = %s", (selected_id,))
    summary = cur.fetchone()
    cur.close()
    if summary:
        m1, m2, m3 = st.columns(3)
        m1.metric("Latest Heart Rate", f"{summary['latest_bpm']} bpm" if summary['latest_bpm'] else "—")
        m2.metric("Latest SpO2", f"{summary['latest_spo2']}%" if summary['latest_spo2'] else "—")
        m3.metric("Total Anomalies", summary['total_anomalies'])
except Exception:
    pass

st.write("")

# Patient summary from stored procedure
st.markdown('<p class="vg-section-label">Patient summary · MySQL stored procedure</p>', unsafe_allow_html=True)
try:
    cur = get_mysql().cursor(dictionary=True)
    cur.callproc("get_patient_summary", (selected_id,))
    results = []
    for result in cur.stored_results():
        results.append(result.fetchall())
    cur.close()
    proc_col1, proc_col2 = st.columns(2, gap="large")
    with proc_col1:
        if results and results[0]:
            r = results[0][0]
            st.write(f"**{r['name']}** · DOB: {r['date_of_birth']}")
            st.write(f"Latest HR: {r['latest_bpm']} bpm · Latest SpO2: {r['latest_spo2']}%")
    with proc_col2:
        if len(results) > 1 and results[1]:
            df_proc = pd.DataFrame(results[1])
            df_proc["logged_at"] = pd.to_datetime(df_proc["logged_at"]).dt.strftime("%H:%M:%S")
            df_proc = df_proc.rename(columns={"reading_type": "Type", "value": "Value", "direction": "Dir", "logged_at": "Time", "threshold": "Threshold"})
            st.dataframe(df_proc, use_container_width=True, hide_index=True)
        else:
            st.info("No anomalies for this patient.")
except Exception as e:
    st.error(f"Procedure error: {e}")

st.write("")

# ── ROW 1: VITALS (left) | ALERT FEED (right) ────────────────────────
col_charts, col_feed = st.columns([2, 1], gap="large")

with col_charts:
    st.markdown('<p class="vg-section-label">Patient vitals · MySQL</p>', unsafe_allow_html=True)
    tab_hr, tab_spo2 = st.tabs(["Heart rate", "SpO2"])

    with tab_hr:
        hr_rows = mysql_client.fetch_recent_heartrate(get_mysql(), selected_id, limit=50)
        if hr_rows:
            hr_annotated = with_rolling_average(hr_rows, "bpm", window_minutes=10)
            df_hr = pd.DataFrame(hr_annotated).sort_values("recorded_at")
            vitals_chart(df_hr, "bpm", "BPM", RED if hr_rows[0]['bpm'] > 140 or hr_rows[0]['bpm'] < 40 else TEAL)
            with st.expander(f"Raw data ({len(df_hr)} rows)"):
                st.dataframe(df_hr.sort_values("recorded_at", ascending=False).rename(columns={"bpm": "BPM", "rolling_avg": "10-min avg", "recorded_at": "Recorded at"}), use_container_width=True, hide_index=True)
        else:
            st.info("No heart rate readings yet.")

    with tab_spo2:
        spo2_rows = mysql_client.fetch_recent_spo2(get_mysql(), selected_id, limit=50)
        if spo2_rows:
            spo2_annotated = with_rolling_average(spo2_rows, "spo2_pct", window_minutes=10)
            df_spo2 = pd.DataFrame(spo2_annotated).sort_values("recorded_at")
            vitals_chart(df_spo2, "spo2_pct", "SpO2 %", RED if spo2_rows[0]['spo2_pct'] < 92 else TEAL)
            with st.expander(f"Raw data ({len(df_spo2)} rows)"):
                st.dataframe(df_spo2.sort_values("recorded_at", ascending=False).rename(columns={"spo2_pct": "SpO2 %", "rolling_avg": "10-min avg", "recorded_at": "Recorded at"}), use_container_width=True, hide_index=True)
        else:
            st.info("No SpO2 readings yet.")

with col_feed:
    st.markdown('<p class="vg-section-label">Alert feed · MongoDB + Neo4j</p>', unsafe_allow_html=True)
    alerts = mongo_client.recent_alerts(conn["mongo_db"], limit=15)
    if not alerts:
        st.info("No alerts yet.")
    else:
        for alert in alerts:
            doctor_name = neo4j_client.doctor_name_by_id(conn["neo4j"], alert.get("notified_doctor_id"))
            severity_class = "" if alert["severity"] == "high" else "amber"
            notify_html = f'<div class="vg-alert-notify">→ notified <b>{doctor_name}</b></div>' if doctor_name else ""
            detail = alert['detail']
            if 'bpm' in detail:
                detail_str = f"bpm: {detail['bpm']} ({detail.get('direction', '')})"
            elif 'spo2_pct' in detail:
                detail_str = f"SpO2: {detail['spo2_pct']}%"
            else:
                detail_str = str(detail)
            st.markdown(f"""
                <div class="vg-alert {severity_class}">
                    <div class="vg-alert-title">{alert['alert_type'].replace('_', ' ').title()} — {patient_names.get(alert['patient_id'], '?')}</div>
                    <div class="vg-alert-meta">{detail_str} · {alert['detected_at'].strftime('%H:%M:%S')}</div>
                    {notify_html}
                </div>""", unsafe_allow_html=True)

st.write("")
st.divider()

# ── ROW 2: ON-CALL DOCTORS | ALERT STATS | ANOMALY LOG ───────────────
col_oncall, col_stats, col_anomaly = st.columns(3, gap="large")

with col_oncall:
    st.markdown('<p class="vg-section-label">On-call doctors · Neo4j</p>', unsafe_allow_html=True)
    oncall = neo4j_client.get_oncall_doctors(conn["neo4j"])
    if oncall:
        for doc in oncall:
            st.markdown(f"""
                <div class="vg-oncall-card">
                    <div class="vg-oncall-name">{doc['doctor']}</div>
                    <div class="vg-oncall-meta">{doc['specialty']} · {doc['patient_count']} patient(s)</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("No doctors on duty.")

with col_stats:
    st.markdown('<p class="vg-section-label">Alert statistics · MongoDB</p>', unsafe_allow_html=True)
    stats = mongo_client.alert_stats_by_patient(conn["mongo_db"])
    if stats:
        for s in stats:
            name = patient_names.get(s["_id"], s["_id"])
            st.markdown(f"""
                <div class="vg-stat-card">
                    <div class="vg-stat-name">{name}</div>
                    <div class="vg-stat-numbers">Total: {s['total_alerts']} · HR: {s['heartrate_alerts']} · SpO2: {s['spo2_alerts']}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("No alert data yet.")

with col_anomaly:
    st.markdown('<p class="vg-section-label">Anomaly log · MySQL trigger</p>', unsafe_allow_html=True)
    try:
        cur = get_mysql().cursor(dictionary=True)
        cur.execute("""
            SELECT p.name, a.reading_type, a.value, a.direction, a.logged_at
            FROM anomaly_log a
            JOIN patients p ON p.patient_id = a.patient_id
            ORDER BY a.logged_at DESC LIMIT 8
        """)
        anomaly_rows = cur.fetchall()
        cur.close()
        if anomaly_rows:
            df_anomaly = pd.DataFrame(anomaly_rows)
            df_anomaly = df_anomaly.rename(columns={"name": "Patient", "reading_type": "Type", "value": "Value", "direction": "Dir", "logged_at": "Time"})
            st.dataframe(df_anomaly, use_container_width=True, hide_index=True)
        else:
            st.info("No anomalies logged yet.")
    except Exception as e:
        st.error(f"Error: {e}")

st.write("")
st.divider()

# ── ROW 3: DEVICE METADATA | DEVICE CORRELATION ──────────────────────
col_mongo, col_neo4j = st.columns(2, gap="large")

with col_mongo:
    st.markdown('<p class="vg-section-label">Device metadata · MongoDB</p>', unsafe_allow_html=True)
    devices = mongo_client.all_device_metadata(conn["mongo_db"])
    if devices:
        df_devices = pd.DataFrame(devices)
        df_devices["_id"] = df_devices["_id"].apply(short_id)
        df_devices["capabilities"] = df_devices["capabilities"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        df_devices = df_devices[["_id", "model", "firmware_version", "battery_pct", "capabilities"]]
        df_devices = df_devices.rename(columns={"_id": "ID", "model": "Model", "firmware_version": "Firmware", "battery_pct": "Bat%", "capabilities": "Capabilities"})
        st.dataframe(df_devices, use_container_width=True, hide_index=True, column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Model": st.column_config.TextColumn(width="medium"),
            "Firmware": st.column_config.TextColumn(width="small"),
            "Bat%": st.column_config.NumberColumn(width="small"),
            "Capabilities": st.column_config.TextColumn(width="large"),
        })
    else:
        st.info("No device metadata found.")

with col_neo4j:
    st.markdown('<p class="vg-section-label">Device correlation · Neo4j + MongoDB</p>', unsafe_allow_html=True)
    st.caption("Patients sharing a device type, with MongoDB alert clustering check.")
    pairs = neo4j_client.device_sharing_pairs(conn["neo4j"])
    if pairs:
        name_to_id = {p["name"]: pid for pid, p in PATIENTS.items()}
        for pair in pairs:
            pid_a = name_to_id.get(pair["patient_a"])
            pid_b = name_to_id.get(pair["patient_b"])
            if pid_a and pid_b:
                pair["Alerts within 1hr"] = "Yes" if mongo_client.patients_alerted_within_hour(
                    conn["mongo_db"], pid_a, pid_b) else "No"
            else:
                pair["Alerts within 1hr"] = "N/A"
        st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
    else:
        st.info("No device-sharing pairs found.")

st.write("")
st.divider()

# ── PERFORMANCE ROW ───────────────────────────────────────────────────
st.markdown('<p class="vg-section-label">System performance</p>', unsafe_allow_html=True)

import time

perf1, perf2, perf3, perf4, perf5 = st.columns(5)

try:
    cur = get_mysql().cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM vitals_heartrate")
    hr_count = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM vitals_spo2")
    spo2_count = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM vitals_activity")
    activity_count = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) AS total FROM vitals_heartrate
        WHERE recorded_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 60 SECOND)
    """)
    recent_count = cur.fetchone()["total"]
    cur.close()

    total_readings = hr_count + spo2_count + activity_count

    perf1.metric("Total readings · MySQL", f"{total_readings:,}")
    perf2.metric("Readings last 60s", recent_count)
except Exception:
    perf1.metric("Total readings · MySQL", "—")
    perf2.metric("Readings last 60s", "—")

try:
    alert_count = conn["mongo_db"].alerts.count_documents({})
    perf3.metric("Alerts fired · MongoDB", alert_count)
except Exception:
    perf3.metric("Alerts fired · MongoDB", "—")

try:
    t0 = time.time()
    neo4j_client.resolve_notified_doctor(conn["neo4j"], selected_id)
    elapsed_ms = round((time.time() - t0) * 1000)
    perf4.metric("Escalation query · Neo4j", f"{elapsed_ms} ms")
except Exception:
    perf4.metric("Escalation query · Neo4j", "—")

try:
    cur2 = get_mysql().cursor(dictionary=True)
    cur2.execute("SELECT COUNT(*) AS total FROM anomaly_log")
    anomaly_count = cur2.fetchone()["total"]
    cur2.close()
    perf5.metric("Anomalies logged · trigger", anomaly_count)
except Exception:
    perf5.metric("Anomalies logged · trigger", "—")

try:
    cur3 = get_mysql().cursor(dictionary=True)
    cur3.execute("SELECT COUNT(*) AS total FROM vitals_heartrate_archive")
    archive_count = cur3.fetchone()["total"]
    cur3.close()
    st.metric("Archived readings · MySQL", f"{archive_count:,}")
except Exception:
    st.metric("Archived readings · MySQL", "—")


try:
    chart_data = pd.DataFrame({
        "Database": ["HR readings", "SpO2 readings", "Activity", "Alerts", "Anomaly log"],
        "Records": [hr_count, spo2_count, activity_count, alert_count, anomaly_count],
        "Color": [TEAL, TEAL, TEAL, RED, AMBER],
    })
    bar = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Database:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Records:Q", title="Records"),
            color=alt.Color("Color:N", scale=None, legend=None),
            tooltip=["Database", "Records"],
        )
        .configure_axis(labelFont="IBM Plex Mono", titleFont="IBM Plex Sans", grid=False)
        .configure_view(strokeWidth=0)
        .properties(height=180)
    )
    st.altair_chart(bar, use_container_width=True)
except Exception:
    pass

st.write("")
st.divider()


st.write("")
st.divider()
col_refresh, col_cap = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Refresh data"):
        get_connections.clear()
        st.rerun()
with col_cap:
    st.caption("Pulls fresh data from MySQL, MongoDB and Neo4j.")
