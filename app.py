"""Predictive maintenance dashboard for the Thales manufacturing data."""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

st.set_page_config(page_title="Thales Predictive Maintenance", page_icon="⚙️", layout="wide")

DATA_FILE = Path(__file__).with_name("Thales_Group_Manufacturing.csv")
FEATURES = [
    "Temperature_C", "Vibration_Hz", "Power_Consumption_kW", "Network_Latency_ms",
    "Packet_Loss_%", "Quality_Control_Defect_Rate_%", "Production_Speed_units_per_hr",
    "Predictive_Maintenance_Score", "Error_Rate_%",
]


@st.cache_data(show_spinner="Loading manufacturing telemetry...")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["event_time"] = pd.to_datetime(df["Date"] + " " + df["Timestamp"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["event_time"]).sort_values(["Machine_ID", "event_time"]).copy()
    # Sensor deviation is the absolute robust deviation from each machine's rolling operating baseline.
    for col in ["Temperature_C", "Vibration_Hz", "Power_Consumption_kW", "Error_Rate_%"]:
        baseline = df.groupby("Machine_ID")[col].transform(lambda s: s.rolling(30, min_periods=10).median())
        scale = df.groupby("Machine_ID")[col].transform(lambda s: s.rolling(30, min_periods=10).std())
        df[f"{col}_deviation"] = ((df[col] - baseline).abs() / scale.replace(0, np.nan)).fillna(0).clip(0, 8)
    df["vibration_power_ratio"] = df["Vibration_Hz"] / df["Power_Consumption_kW"].clip(lower=0.1)
    df["error_trend"] = df.groupby("Machine_ID")["Error_Rate_%"].transform(lambda s: s.diff(10)).fillna(0)
    return df


@st.cache_data(show_spinner="Scoring anomalies with Isolation Forest...")
def score_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    model_features = FEATURES + [
        "Temperature_C_deviation", "Vibration_Hz_deviation", "Power_Consumption_kW_deviation",
        "Error_Rate_%_deviation", "vibration_power_ratio", "error_trend",
    ]
    X = work[model_features].replace([np.inf, -np.inf], np.nan).fillna(0)
    scaler = RobustScaler()
    scaled = scaler.fit_transform(X)
    sample = scaled if len(scaled) <= 50000 else scaled[np.linspace(0, len(scaled) - 1, 50000, dtype=int)]
    model = IsolationForest(n_estimators=180, contamination=0.08, random_state=42, n_jobs=-1)
    model.fit(sample)
    raw = -model.score_samples(scaled)
    work["anomaly_score"] = (100 * (raw - raw.min()) / (raw.max() - raw.min() + 1e-9)).round(1)
    work["risk_level"] = pd.cut(work["anomaly_score"], [-1, 45, 70, 101], labels=["Low", "Medium", "High"])
    work["inspection_priority"] = np.select(
        [work["risk_level"].eq("High"), work["risk_level"].eq("Medium")],
        ["Inspect within 24 hours", "Inspect this week"], default="Monitor routinely"
    )
    return work


def chart(frame: pd.DataFrame, y: str, title: str, color: str = "#38bdf8"):
    return alt.Chart(frame).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X("event_time:T", title="Time"), y=alt.Y(f"{y}:Q", title=title),
        tooltip=["event_time:T", "Machine_ID:N", alt.Tooltip(f"{y}:Q", format=".2f"), "risk_level:N"],
    ).properties(height=260).interactive()


df = score_anomalies(load_data(str(DATA_FILE)))
st.title("Predictive Maintenance Command Center")
st.caption("Machine health analytics using rolling sensor baselines and Isolation Forest anomaly detection.")

with st.sidebar:
    st.header("Analysis controls")
    machine_options = sorted(df["Machine_ID"].unique())
    selected_machines = st.multiselect("Machine selector", machine_options, default=machine_options[:1])
    threshold = st.slider("Risk threshold", 0, 100, 70, help="Scores at or above this value are priority alerts.")
    earliest, latest = df["event_time"].min().date(), df["event_time"].max().date()
    dates = st.date_input("Time window", value=(max(earliest, latest - pd.Timedelta(days=2)), latest), min_value=earliest, max_value=latest)
    modes = st.multiselect("Operation mode", sorted(df["Operation_Mode"].unique()), default=sorted(df["Operation_Mode"].unique()))
    st.divider()
    st.caption("High: urgent maintenance | Medium: early warning | Low: normal behavior")

if not selected_machines:
    st.info("Select at least one machine to begin.")
    st.stop()
start, end = (dates if isinstance(dates, tuple) else (dates, dates))
filtered = df[
    df["Machine_ID"].isin(selected_machines)
    & df["Operation_Mode"].isin(modes)
    & df["event_time"].dt.date.between(start, end)
].copy()
if filtered.empty:
    st.warning("No readings match the current filters.")
    st.stop()
priority = filtered[filtered["anomaly_score"] >= threshold]

overview, anomalies, alerts, history = st.tabs([
    "Maintenance overview", "Machine anomaly dashboard", "Maintenance alerts", "Historical risk analysis"
])
with overview:
    a, b, c, d = st.columns(4)
    a.metric("Readings analysed", f"{len(filtered):,}")
    b.metric("Priority alerts", f"{len(priority):,}", f"{len(priority) / len(filtered):.1%} of filtered data")
    high_machines = priority["Machine_ID"].nunique()
    c.metric("High-risk assets", high_machines)
    d.metric("Mean anomaly score", f"{filtered['anomaly_score'].mean():.1f}/100")
    st.subheader("Risk distribution across selected machines")
    risk_counts = filtered.groupby(["Machine_ID", "risk_level"], observed=False).size().reset_index(name="readings")
    st.altair_chart(alt.Chart(risk_counts).mark_bar().encode(
        x=alt.X("Machine_ID:N", title="Machine"), y=alt.Y("readings:Q", title="Readings"),
        color=alt.Color("risk_level:N", scale=alt.Scale(domain=["Low", "Medium", "High"], range=["#22c55e", "#f59e0b", "#ef4444"])) ,
        tooltip=["Machine_ID:N", "risk_level:N", "readings:Q"]
    ).properties(height=320), use_container_width=True)
    st.subheader("Highest current risk assets")
    latest_rows = filtered.sort_values("event_time").groupby("Machine_ID").tail(1).sort_values("anomaly_score", ascending=False)
    st.dataframe(latest_rows[["Machine_ID", "event_time", "Operation_Mode", "anomaly_score", "risk_level", "inspection_priority"]], use_container_width=True, hide_index=True)

with anomalies:
    st.subheader("Anomaly score trend")
    st.altair_chart(chart(filtered, "anomaly_score", "Anomaly score", "#ef4444"), use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Sensor deviation")
        deviation = filtered.melt(id_vars=["event_time"], value_vars=["Temperature_C_deviation", "Vibration_Hz_deviation", "Power_Consumption_kW_deviation", "Error_Rate_%_deviation"], var_name="sensor", value_name="deviation")
        st.altair_chart(alt.Chart(deviation).mark_line().encode(x="event_time:T", y=alt.Y("deviation:Q", title="Standard deviations from baseline"), color="sensor:N").properties(height=280).interactive(), use_container_width=True)
    with right:
        st.subheader("Operational context")
        st.altair_chart(chart(filtered, "Error_Rate_%", "Error rate percent", "#8b5cf6"), use_container_width=True)

with alerts:
    st.subheader(f"Alerts at score {threshold} or higher")
    alert_cols = ["event_time", "Machine_ID", "Operation_Mode", "anomaly_score", "risk_level", "inspection_priority", "Temperature_C", "Vibration_Hz", "Error_Rate_%"]
    st.dataframe(priority.sort_values(["anomaly_score", "event_time"], ascending=[False, False])[alert_cols], use_container_width=True, hide_index=True)
    st.download_button("Download filtered alert list", priority[alert_cols].to_csv(index=False).encode("utf-8"), "maintenance_alerts.csv", "text/csv")
    st.caption("Priority uses the selected anomaly-score threshold; it is a decision-support signal, not an automatic shutdown command.")

with history:
    st.subheader("Risk escalation timeline")
    hourly = filtered.set_index("event_time").groupby("Machine_ID")["anomaly_score"].resample("1h").mean().reset_index()
    st.altair_chart(alt.Chart(hourly).mark_line().encode(x="event_time:T", y=alt.Y("anomaly_score:Q", title="Mean hourly anomaly score"), color="Machine_ID:N", tooltip=["event_time:T", "Machine_ID:N", alt.Tooltip("anomaly_score:Q", format=".1f")]).properties(height=330).interactive(), use_container_width=True)
    st.subheader("Post-maintenance comparison proxy")
    st.write("Compare anomaly patterns around records labelled `Maintenance` to assess whether sensor behavior stabilizes after maintenance windows.")
    comparison = filtered.groupby("Operation_Mode")["anomaly_score"].agg(["count", "mean", "median", "max"]).round(1)
    st.dataframe(comparison, use_container_width=True)

st.divider()
st.caption("Method: machine-specific rolling median baselines, engineered deviation/trend features, and Isolation Forest scoring. Refreshing filters does not retrain the model.")
