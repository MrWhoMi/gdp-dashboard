import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def format_time(minutes):
    total_seconds = int(minutes * 60)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

st.set_page_config(layout="wide")

st.title("📊 Race Analysis & Simulation")

# ---------- LOAD ----------
if "segments_df" not in st.session_state:
    st.warning("Go to Race Plan page first")
    st.stop()

# 🔥 COPY (DO NOT MODIFY ORIGINAL)
segments_df = st.session_state["segments_df"].copy()
cutoff_time = st.session_state.get("cutoff_time", 8.0)

# ---------- INPUT ----------
st.subheader("🎯 Simulation Input")

col1, col2 = st.columns(2)

base_pace = col1.number_input(
    "Base Pace (min/km - flat)",
    value=6.0
)

fatigue_factor = col2.slider(
    "Fatigue Factor",
    0.0, 1.0, 0.3
)

from datetime import datetime, timedelta

race_start = st.time_input("Race Start Time", value=datetime.strptime("05:00", "%H:%M"))

def add_clock(start_time, minutes):
    return (datetime.combine(datetime.today(), start_time) + timedelta(minutes=minutes)).time()



#---- MAX PACE -----

difficulty_factor = segments_df["type"].map({
    "Steep": 1.8,
    "Uphill": 1.4,
    "Flat": 1.0,
    "Downhill": 0.9
})

weighted_distance = (segments_df["distance"] * difficulty_factor).sum()

required_pace_adjusted = (cutoff_time * 60) / weighted_distance

st.metric("Required Effort Pace", f"{required_pace_adjusted:.2f}")

# ---------- PACE MODEL ----------
def adjust_pace(row):
    pace = base_pace

    if row["type"] == "Steep":
        pace *= 1.8
    elif row["type"] == "Uphill":
        pace *= 1.4
    elif row["type"] == "Downhill":
        pace *= 0.85
    elif row["type"] == "Flat":
        pace *= 1.0

    # fatigue accumulation
    fatigue = 1 + (row.name * fatigue_factor * 0.02)

    return pace * fatigue

segments_df["pace"] = segments_df.apply(adjust_pace, axis=1)

# ---------- TIME ----------
segments_df["time_min"] = segments_df["pace"] * segments_df["distance"]
segments_df["cum_time"] = segments_df["time_min"].cumsum()

segments_df["ETA"] = segments_df["cum_time"].apply(lambda x: add_clock(race_start, x))
# ---------- SUMMARY ----------
st.subheader("⏱️ Race Prediction")

total_time = segments_df["time_min"].sum()
total_hours = total_time / 60

col1, col2 = st.columns(2)

segments_df["Segment Time"] = segments_df["time_min"].apply(format_time)
segments_df["Cumulative Time"] = segments_df["cum_time"].apply(format_time)

if total_hours > cutoff_time:
    st.error("⚠️ You will MISS cut-off")
else:
    st.success("✅ You are within cut-off")

# ---------- PACE CHART ----------
st.subheader("📋 Segment Breakdown (Race Clock)")

display_df = segments_df.copy()

display_df["KM"] = display_df["end_km"].round(1)
display_df["Pace"] = display_df["pace"].round(2)
display_df["Segment Time"] = display_df["time_min"].apply(format_time)
display_df["Cumulative Time"] = display_df["cum_time"].apply(format_time)
display_df["ETA"] = display_df["ETA"].astype(str)

st.dataframe(display_df[[
    "KM",
    "type",
    "Pace",
    "Segment Time",
    "Cumulative Time",
    "ETA"
]], use_container_width=True)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=segments_df["end_km"],
    y=segments_df["pace"],
    mode="lines+markers",
    line=dict(color="#4cc9f0"),
    name="Pace"
))

fig.update_layout(
    xaxis_title="KM",
    yaxis_title="min/km",
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# ---------- OPTIONAL TABLE ----------
st.subheader("📋 Segment Breakdown")

st.dataframe(segments_df[[
    "type", "start_km", "end_km", "distance", "pace", "time_min"
]], use_container_width=True)