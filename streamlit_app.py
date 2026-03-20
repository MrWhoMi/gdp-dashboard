import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="Race Command Center")

# ---------- RACE CONFIG ----------
RACE_DATE = datetime(2026, 8, 30)
DISTANCE = 42
ELEVATION = 2000
LOCATION = "Bandung"

# ---------- MOCK TRAINING LOGIC ----------
today = datetime.today()
days_to_race = (RACE_DATE - today).days

# Weekly pattern generator
def get_today_workout(day_index):
    pattern = ["Rest", "Easy Run", "Rest", "Speed", "Rest", "Long Run", "Recovery"]
    return pattern[day_index % 7]

today_workout = get_today_workout(today.weekday())

# ---------- WEATHER (STATIC FOR NOW) ----------
weather = {
    "temp": 24,
    "condition": "Cloudy",
    "humidity": 78
}

# ---------- MOCK DATA ----------
dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
df = pd.DataFrame({
    "date": dates,
    "distance": np.random.randint(5, 20, size=30),
    "elevation": np.random.randint(100, 500, size=30)
})

# ---------- HEADER ----------
st.title("🏁 Race Command Center")

# ---------- TOP METRICS ----------
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("D-Day", f"{days_to_race} days")
col2.metric("Distance", f"{DISTANCE} KM")
col3.metric("Elevation", f"{ELEVATION} m")
col4.metric("Location", LOCATION)
col5.metric("Weather", f"{weather['temp']}°C, {weather['condition']}")

st.divider()

# ---------- MAIN LAYOUT ----------
left, center, right = st.columns([1.2, 1.5, 1])

# ---------- LEFT: MAP + ELEVATION ----------
with left:
    st.subheader("🗺️ Course Overview")

    st.info("GPX map will be displayed here")

    st.subheader("Elevation Profile")
    st.line_chart(df.set_index("date")["elevation"])

# ---------- CENTER: WEEKLY TRAINING ----------
with center:
    st.subheader("📅 Weekly Training Structure")

    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_plan = ["Rest", "Easy", "Rest", "Speed", "Rest", "Long Run", "Recovery"]

    cols = st.columns(7)

    for i, day in enumerate(week_days):
        with cols[i]:
            st.markdown(f"**{day}**")
            st.info(week_plan[i])

# ---------- RIGHT: TODAY PANEL ----------
with right:
    st.subheader("📌 Today Focus")

    st.success(f"Workout: {today_workout}")

    if today_workout == "Long Run":
        st.info("Focus: Endurance + fueling")
    elif today_workout == "Speed":
        st.warning("Focus: Intervals, control effort")
    elif today_workout == "Easy Run":
        st.info("Focus: Recovery pace")
    else:
        st.write("Rest / Recovery")

    st.subheader("⚠️ Alerts")

    if df["distance"].sum() < 50:
        st.error("Low weekly mileage")
    else:
        st.success("Training on track")

# ---------- BOTTOM SECTION ----------
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Distance Trend")
    st.line_chart(df.set_index("date")["distance"])

with col2:
    st.subheader("⛰️ Elevation Trend")
    st.area_chart(df.set_index("date")["elevation"])