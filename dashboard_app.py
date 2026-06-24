"""
VitalGraph: Streamlit dashboard.

Connects directly to MySQL, MongoDB, and Neo4j using the same client
modules the router uses (router/db/*) — no separate API layer needed.
See SPEC.md for the full architecture and rationale.

Run with:
    streamlit run dashboard/app.py
(run from the vitalgraph/ project root)
"""

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

st.set_page_config(page_title="VitalGraph", page_icon="💓", layout="wide")


@st.cache_resource
def get_connections():
    """
    Cached so Streamlit doesn't reopen connections on every rerun (Streamlit
    reruns the whole script on each interaction, e.g. switching patients).
    """
    return {
        "mysql": mysql_client.get_connection(),
        "mongo_db": mongo_client.get_db(mongo_client.get_client()),
        "neo4j": neo4j_client.get_driver(),
    }


conn = get_connections()

st.title("💓 VitalGraph")
st.caption("Polyglot health monitoring console — MQTT · MySQL · MongoDB · Neo4j")

# --- Patient selector ---
patients = mysql_client.fetch_all_patients(conn["mysql"])
patient_names = {p["patient_id"]: p["name"] for p in patients}


def short_id(full_id: str) -> str:
    """Show a short, readable prefix instead of the full UUID — the full
    ID still drives every query under the hood, this is purely display."""
    return full_id.split("-")[0]


def vitals_chart(df: pd.DataFrame, value_col: str, value_label: str, color: str):
    """
    Explicit Altair chart so axis scaling is predictable (line_chart's
    auto-scaling can produce odd tick labels on small numeric ranges).
    Draws the raw reading plus the rolling-average overlay.
    """
    melted = df.melt(
        id_vars=["recorded_at"],
        value_vars=[value_col, "rolling_avg"],
        var_name="series",
        value_name="value",
    )
    melted["series"] = melted["series"].map({
        value_col: value_label, "rolling_avg": "10-min rolling avg"
    })
    chart = (
        alt.Chart(melted)
        .mark_line()
        .encode(
            x=alt.X("recorded_at:T", title="Time"),
            y=alt.Y("value:Q", title=value_label, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(domain=[value_label, "10-min rolling avg"], range=[color, "#94A3B8"]),
            ),
            strokeDash=alt.condition(
                alt.datum.series == "10-min rolling avg", alt.value([4, 3]), alt.value([1, 0])
            ),
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)


with st.expander("📋 Patients table (MySQL)"):
    df_patients = pd.DataFrame(patients)
    df_patients["patient_id"] = df_patients["patient_id"].apply(short_id)
    df_patients = df_patients.rename(
        columns={"patient_id": "ID", "name": "Name", "date_of_birth": "Date of birth"}
    )
    st.dataframe(df_patients, use_container_width=True, hide_index=True)

selected_id = st.radio(
    "Patient",
    options=list(patient_names.keys()),
    format_func=lambda pid: patient_names[pid],
    horizontal=True,
)

col_charts, col_feed = st.columns([2, 1])

with col_charts:
    # --- Heart rate chart ---
    st.subheader("Heart rate")
    hr_rows = mysql_client.fetch_recent_heartrate(conn["mysql"], selected_id, limit=50)
    if hr_rows:
        hr_annotated = with_rolling_average(hr_rows, "bpm", window_minutes=10)
        df_hr = pd.DataFrame(hr_annotated).sort_values("recorded_at")
        vitals_chart(df_hr, "bpm", "BPM", "#E07856")
        st.metric("Latest reading", f"{hr_rows[0]['bpm']} bpm")
        with st.expander(f"Raw data ({len(df_hr)} rows from MySQL)"):
            st.dataframe(
                df_hr.sort_values("recorded_at", ascending=False)
                .rename(columns={"bpm": "BPM", "rolling_avg": "10-min rolling avg", "recorded_at": "Recorded at"}),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No heart rate readings yet — start the publisher and router.")

    # --- SpO2 chart ---
    st.subheader("SpO2")
    spo2_rows = mysql_client.fetch_recent_spo2(conn["mysql"], selected_id, limit=50)
    if spo2_rows:
        spo2_annotated = with_rolling_average(spo2_rows, "spo2_pct", window_minutes=10)
        df_spo2 = pd.DataFrame(spo2_annotated).sort_values("recorded_at")
        vitals_chart(df_spo2, "spo2_pct", "SpO2 %", "#3E7C8C")
        st.metric("Latest reading", f"{spo2_rows[0]['spo2_pct']}%")
        with st.expander(f"Raw data ({len(df_spo2)} rows from MySQL)"):
            st.dataframe(
                df_spo2.sort_values("recorded_at", ascending=False)
                .rename(columns={"spo2_pct": "SpO2 %", "rolling_avg": "10-min rolling avg", "recorded_at": "Recorded at"}),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No SpO2 readings yet.")

    # --- Care network ---
    st.subheader("Care network")
    resolution = neo4j_client.resolve_notified_doctor(conn["neo4j"], selected_id)
    if resolution:
        st.write(f"**Patient:** {patient_names[selected_id]}")
        st.write(f"**Primary doctor:** {resolution['primary_doctor_name']}")
        if resolution["doctor_name"] != resolution["primary_doctor_name"]:
            st.error(
                f"⚠️ Primary off duty — escalated to **{resolution['doctor_name']}**"
            )
        else:
            st.success("✅ Primary doctor on duty — no escalation needed")
    else:
        st.warning("No care network found for this patient.")

with col_feed:
    st.subheader("Alert feed")
    alerts = mongo_client.recent_alerts(conn["mongo_db"], limit=20)
    if not alerts:
        st.info("No alerts yet — all patients stable.")
    else:
        for alert in alerts:
            doctor_name = neo4j_client.doctor_name_by_id(
                conn["neo4j"], alert.get("notified_doctor_id")
            )
            with st.container(border=True):
                severity_icon = "🔴" if alert["severity"] == "high" else "🟡"
                st.markdown(f"{severity_icon} **{alert['alert_type'].replace('_', ' ').title()}**")
                st.caption(patient_names.get(alert["patient_id"], alert["patient_id"]))
                st.caption(str(alert["detail"]))
                st.caption(alert["detected_at"].strftime("%H:%M:%S"))
                if doctor_name:
                    st.markdown(f"→ notified **{doctor_name}**")

st.divider()
st.subheader("Raw data across all three databases")
tab_mongo, tab_neo4j = st.tabs(["📄 Device metadata (MongoDB)", "🕸️ Device correlation insight (Neo4j)"])

with tab_mongo:
    st.caption(
        "Each device model has genuinely different fields — the chest strap "
        "has no spo2/steps capability, for example. This is why device "
        "metadata lives in MongoDB rather than a fixed SQL schema (see SPEC.md §6)."
    )
    devices = mongo_client.all_device_metadata(conn["mongo_db"])
    if devices:
        df_devices = pd.DataFrame(devices)
        df_devices["_id"] = df_devices["_id"].apply(short_id)
        df_devices = df_devices.rename(columns={
            "_id": "Device ID", "model": "Model", "firmware_version": "Firmware",
            "battery_pct": "Battery %", "capabilities": "Capabilities",
            "last_seen": "Last seen",
        })
        st.dataframe(df_devices, use_container_width=True, hide_index=True)
    else:
        st.info("No device metadata found.")

with tab_neo4j:
    st.caption(
        "Patients sharing the same device model — a real signal for "
        "spotting a potentially faulty device batch. This is a graph "
        "traversal query, not a stored table (see SPEC.md §7, Query 3)."
    )
    pairs = neo4j_client.device_sharing_pairs(conn["neo4j"])
    if pairs:
        st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
    else:
        st.info("No device-sharing pairs found.")

st.divider()
st.caption(
    "Auto-refresh: rerun this page or use Streamlit's built-in rerun (top-right ⋮ menu) "
    "to pull the latest data from MQTT-fed readings."
)
