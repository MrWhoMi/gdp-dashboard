import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import streamlit as st
st.title("TEST PAGE")

st.write("Training Page Loaded")
st.set_page_config(layout="wide")

st.title("📅 Training Dashboard")

# ---------- CONFIG ----------
RACE_DATE = datetime(2026, 8, 30)
START_DATE = datetime.today()

# ---------- TRAINING STRUCTURE ----------
def generate_training_plan(start_date, race_date):
    days = (race_date - start_date).days
    plan = []

    for i in range(days):
        current_day = start_date + timedelta(days=i)
        weekday = current_day.weekday()

        # Pattern:
        # Sat/Sun Long Run
        # +2 days Easy
        # +2 days Speed
        if weekday in [5, 6]:
            workout = "Long Run"
        elif weekday == 1:
            workout = "Easy Run"
        elif weekday == 3:
            workout = "Speed"
        else:
            workout = "Rest"

        plan.append({
            "date": current_day,
            "day": current_day.strftime("%A"),
            "workout": workout
        })

    return pd.DataFrame(plan)

df = generate_training_plan(START_DATE, RACE_DATE)

# ---------- FILTER ----------
st.subheader("📆 Upcoming 14 Days")

upcoming = df[df["date"] <= datetime.today() + timedelta(days=14)]

st.dataframe(upcoming, use_container_width=True)

# ---------- WEEKLY VIEW ----------
st.subheader("📊 Weekly Structure")

week_df = df[df["date"] <= datetime.today() + timedelta(days=7)]

cols = st.columns(7)

for i, row in enumerate(week_df.head(7).itertuples()):
    with cols[i]:
        st.markdown(f"**{row.day[:3]}**")

        if row.workout == "Long Run":
            st.error("Long")
        elif row.workout == "Speed":
            st.warning("Speed")
        elif row.workout == "Easy Run":
            st.success("Easy")
        else:
            st.write("Rest")

# ---------- SUMMARY ----------
st.subheader("📈 Weekly Summary")

weekly_counts = df.groupby("workout").size()

col1, col2, col3 = st.columns(3)

col1.metric("Long Runs", int(weekly_counts.get("Long Run", 0)))
col2.metric("Speed Sessions", int(weekly_counts.get("Speed", 0)))
col3.metric("Easy Runs", int(weekly_counts.get("Easy Run", 0)))

# ---------- NEXT KEY SESSION ----------
st.subheader("🎯 Next Key Session")

next_key = df[df["workout"].isin(["Long Run", "Speed"])].iloc[0]

st.info(f"{next_key['day']} - {next_key['workout']}")