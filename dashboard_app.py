"""
VitalGraph dashboard. Run: streamlit run dashboard_app.py
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

st.set_page_config(page_title="VitalGraph", page_icon="🩺", layout="wide")

# Color tokens — dark clinical theme
INK = "#E8E6E1"
PAPER = "#16191D"
PANEL = "#1F2329"
HAIRLINE = "#2B3036"
TEAL = "#4FB3A3"
TEAL_SOFT = "#1B2E2B"
RED = "#E0654A"
RED_SOFT = "#332220"
AMBER = "#D9A23B"
MUTED = "#8B939B"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {INK};
}}
.stApp {{
    background-color: {PAPER};
}}
header[data-testid="stHeader"] {{
    background-color: {PAPER};
}}
header[data-testid="stHeader"] * {{
    color: {INK} !important;
    fill: {INK} !important;
}}
div[data-testid="stToolbar"] {{
    color: {INK};
}}
section[data-testid="stSidebar"] {{
    background-color: {PANEL};
    border-right: 1px solid {HAIRLINE};
}}
h1, h2, h3, h4, h5 {{
    font-family: 'Source Serif 4', serif;
    color: {INK};
    letter-spacing: -0.01em;
}}
.vg-eyebrow {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {MUTED};
    margin-bottom: 0.15rem;
}}
.vg-brand {{
    font-family: 'Source Serif 4', serif;
    font-weight: 700;
    font-size: 1.5rem;
    color: {INK};
    margin: 0;
}}
.vg-brand-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: {MUTED};
    margin-top: 0.1rem;
}}
hr, [data-testid="stDivider"] {{
    border-color: {HAIRLINE} !important;
}}

/* Care-network strip: the signature element. A patient-chart-header
   feel — left border carries the status color, name set in serif. */
.vg-strip {{
    background: {PANEL};
    border: 1px solid {HAIRLINE};
    border-left: 5px solid {TEAL};
    border-radius: 4px;
    padding: 1.1rem 1.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
}}
.vg-strip.escalated {{ border-left-color: {RED}; background: {RED_SOFT}; }}
.vg-strip.stable {{ border-left-color: {TEAL}; background: {TEAL_SOFT}; }}
.vg-strip-name {{
    font-family: 'Source Serif 4', serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: {INK};
}}
.vg-strip-meta {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: {MUTED};
}}
.vg-status-pill {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.45rem 0.9rem;
    border-radius: 20px;
    white-space: nowrap;
}}
.vg-status-pill.escalated {{ background: {RED}; color: white; }}
.vg-status-pill.stable {{ background: {TEAL}; color: white; }}

.vg-section-label {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {MUTED};
    border-bottom: 1px solid {HAIRLINE};
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
}}

/* Alert cards */
.vg-alert {{
    background: {PANEL};
    border: 1px solid {HAIRLINE};
    border-left: 4px solid {RED};
    border-radius: 4px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.7rem;
}}
.vg-alert.amber {{ border-left-color: {AMBER}; }}
.vg-alert-title {{
    font-weight: 600;
    font-size: 0.95rem;
    color: {INK};
}}
.vg-alert-meta {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.74rem;
    color: {MUTED};
    margin-top: 0.2rem;
}}
.vg-alert-notify {{
    font-size: 0.85rem;
    margin-top: 0.4rem;
    color: {INK};
}}
.vg-alert-notify b {{ color: {TEAL}; }}

[data-testid="stMetricValue"] {{
    font-family: 'Source Serif 4', serif;
    color: {INK};
}}
[data-testid="stMetricLabel"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {MUTED};
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 500;
    color: {MUTED};
}}

/* Dark-mode overrides for native Streamlit widgets, which otherwise
   keep their own light-mode internal styling. */
[data-testid="stExpander"] {{
    background-color: {PANEL};
    border: 1px solid {HAIRLINE};
    border-radius: 4px;
}}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
    background-color: {PANEL};
}}
.stRadio label {{
    color: {INK} !important;
}}
[data-testid="stMarkdownContainer"] p {{
    color: {INK};
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {MUTED} !important;
}}
[data-testid="stAlert"] {{
    background-color: {PANEL};
    border: 1px solid {HAIRLINE};
}}
hr {{
    background-color: {HAIRLINE} !important;
}}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_connections():
    """Cached so Streamlit doesn't reopen connections on every rerun."""
    return {
        "mysql": mysql_client.get_connection(),
        "mongo_db": mongo_client.get_db(mongo_client.get_client()),
        "neo4j": neo4j_client.get_driver(),
    }


conn = get_connections()


def short_id(full_id: str) -> str:
    """Show a short, readable prefix instead of the full UUID — the full
    ID still drives every query under the hood, this is purely display."""
    return full_id.split("-")[0]


def vitals_chart(df: pd.DataFrame, value_col: str, value_label: str, color: str):
    """Heart-rate/SpO2 line chart with rolling-average overlay."""
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
                scale=alt.Scale(domain=[value_label, "10-min rolling avg"], range=[color, MUTED]),
            ),
            strokeDash=alt.condition(
                alt.datum.series == "10-min rolling avg", alt.value([4, 3]), alt.value([1, 0])
            ),
        )
        .configure_axis(labelFont="IBM Plex Mono", titleFont="IBM Plex Sans", grid=False,
                         labelColor=MUTED, titleColor=MUTED, domainColor=HAIRLINE)
        .configure_view(strokeWidth=0, fill=PANEL)
        .configure(background=PANEL)
        .configure_legend(labelColor=MUTED, titleColor=MUTED)
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)


# Sidebar: brand, patient selector, patients table
patients = mysql_client.fetch_all_patients(conn["mysql"])
patient_names = {p["patient_id"]: p["name"] for p in patients}

with st.sidebar:
    st.markdown(
        '<p class="vg-brand">🩺 VitalGraph</p>'
        '<p class="vg-brand-sub">MQTT · MYSQL · MONGODB · NEO4J</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown('<p class="vg-eyebrow">Patient</p>', unsafe_allow_html=True)
    selected_id = st.radio(
        "Patient",
        options=list(patient_names.keys()),
        format_func=lambda pid: patient_names[pid],
        label_visibility="collapsed",
    )

    st.divider()
    with st.expander("Patients table (MySQL)"):
        df_patients = pd.DataFrame(patients)
        df_patients["patient_id"] = df_patients["patient_id"].apply(short_id)
        df_patients = df_patients.rename(
            columns={"patient_id": "ID", "name": "Name", "date_of_birth": "Date of birth"}
        )
        st.dataframe(df_patients, use_container_width=True, hide_index=True)


# Care-network / escalation banner
resolution = neo4j_client.resolve_notified_doctor(conn["neo4j"], selected_id)
if resolution:
    escalated = resolution["doctor_name"] != resolution["primary_doctor_name"]
    state_class = "escalated" if escalated else "stable"
    status_text = (
        f"Escalated to {resolution['doctor_name']}" if escalated
        else f"On duty — {resolution['doctor_name']} notified directly"
    )
    st.markdown(
        f"""
        <div class="vg-strip {state_class}">
            <div>
                <div class="vg-eyebrow">Care network</div>
                <div class="vg-strip-name">{patient_names[selected_id]}</div>
                <div class="vg-strip-meta">PRIMARY: {resolution['primary_doctor_name'].upper()}</div>
            </div>
            <div class="vg-status-pill {state_class}">{status_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("No care network found for this patient.")

st.write("")


# Vitals (left) vs alert feed (right)
col_charts, col_feed = st.columns([2, 1], gap="large")

with col_charts:
    st.markdown('<p class="vg-section-label">This patient\'s vitals</p>', unsafe_allow_html=True)

    tab_hr, tab_spo2 = st.tabs(["Heart rate", "SpO2"])

    with tab_hr:
        hr_rows = mysql_client.fetch_recent_heartrate(conn["mysql"], selected_id, limit=50)
        if hr_rows:
            hr_annotated = with_rolling_average(hr_rows, "bpm", window_minutes=10)
            df_hr = pd.DataFrame(hr_annotated).sort_values("recorded_at")
            st.metric("Latest reading", f"{hr_rows[0]['bpm']} bpm")
            vitals_chart(df_hr, "bpm", "BPM", RED if hr_rows[0]['bpm'] > 140 or hr_rows[0]['bpm'] < 40 else TEAL)
            with st.expander(f"Raw data ({len(df_hr)} rows from MySQL)"):
                st.dataframe(
                    df_hr.sort_values("recorded_at", ascending=False)
                    .rename(columns={"bpm": "BPM", "rolling_avg": "10-min rolling avg", "recorded_at": "Recorded at"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No heart rate readings yet — start the publisher and router.")

    with tab_spo2:
        spo2_rows = mysql_client.fetch_recent_spo2(conn["mysql"], selected_id, limit=50)
        if spo2_rows:
            spo2_annotated = with_rolling_average(spo2_rows, "spo2_pct", window_minutes=10)
            df_spo2 = pd.DataFrame(spo2_annotated).sort_values("recorded_at")
            st.metric("Latest reading", f"{spo2_rows[0]['spo2_pct']}%")
            vitals_chart(df_spo2, "spo2_pct", "SpO2 %", RED if spo2_rows[0]['spo2_pct'] < 92 else TEAL)
            with st.expander(f"Raw data ({len(df_spo2)} rows from MySQL)"):
                st.dataframe(
                    df_spo2.sort_values("recorded_at", ascending=False)
                    .rename(columns={"spo2_pct": "SpO2 %", "rolling_avg": "10-min rolling avg", "recorded_at": "Recorded at"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No SpO2 readings yet.")

with col_feed:
    st.markdown('<p class="vg-section-label">Alert feed — all patients</p>', unsafe_allow_html=True)
    alerts = mongo_client.recent_alerts(conn["mongo_db"], limit=20)
    if not alerts:
        st.info("No alerts yet — all patients stable.")
    else:
        for alert in alerts:
            doctor_name = neo4j_client.doctor_name_by_id(
                conn["neo4j"], alert.get("notified_doctor_id")
            )
            severity_class = "" if alert["severity"] == "high" else "amber"
            notify_html = f'<div class="vg-alert-notify">→ notified <b>{doctor_name}</b></div>' if doctor_name else ""
            st.markdown(
                f"""
                <div class="vg-alert {severity_class}">
                    <div class="vg-alert-title">{alert['alert_type'].replace('_', ' ').title()} — {patient_names.get(alert['patient_id'], alert['patient_id'])}</div>
                    <div class="vg-alert-meta">{alert['detail']} · {alert['detected_at'].strftime('%H:%M:%S')}</div>
                    {notify_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


# System-wide views: MongoDB + Neo4j side by side
st.write("")
st.divider()
st.markdown('<p class="vg-section-label">System-wide data — MongoDB + Neo4j</p>', unsafe_allow_html=True)

col_mongo, col_neo4j = st.columns(2, gap="large")

with col_mongo:
    st.markdown("**Device metadata** &nbsp;·&nbsp; *MongoDB*")
    st.caption(
        "Each device model has genuinely different fields — the chest strap "
        "has no spo2/steps capability, for example. This is why device "
        "metadata lives in MongoDB rather than a fixed SQL schema."
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

with col_neo4j:
    st.markdown("**Device correlation insight** &nbsp;·&nbsp; *Neo4j*")
    st.caption(
        "Patients sharing the same device model — a real signal for "
        "spotting a potentially faulty device batch. A graph traversal "
        "query, not a stored table."
    )
    pairs = neo4j_client.device_sharing_pairs(conn["neo4j"])
    if pairs:
        st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
    else:
        st.info("No device-sharing pairs found.")

st.write("")
st.divider()
st.caption(
    "Auto-refresh: rerun this page or use Streamlit's built-in rerun (top-right ⋮ menu) "
    "to pull the latest data from MQTT-fed readings."
)
