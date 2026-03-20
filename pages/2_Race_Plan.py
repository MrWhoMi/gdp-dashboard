import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from utils.gpx_parser import parse_gpx, group_segments, resample_by_distance, merge_small_segments
from utils.calculations import fix_segment_gaps

st.set_page_config(layout="wide")

st.title("Race Plan & Course Analysis")

uploaded_file = st.file_uploader("Upload your GPX route", type=["gpx"])

if uploaded_file or "df_raw" in st.session_state:

    # ---------- LOAD ----------
    
    if uploaded_file:
        df_raw, wp_df = parse_gpx(uploaded_file)
        st.session_state["df_raw"] = df_raw
        st.session_state["wp_df"] = wp_df
    else:
        df_raw = st.session_state["df_raw"]
        wp_df = st.session_state["wp_df"]

    if "df_raw" in st.session_state:
        st.success("GPX Loaded (from memory)")


    df_raw["cum_distance"] -= df_raw["cum_distance"].min()
    df_raw = df_raw.sort_values("cum_distance").reset_index(drop=True)

    water_df = wp_df[
    wp_df["symbol"].str.contains("Drinking Water", case=False, na=False)
    ]

    # ---------- RESAMPLE ----------
    df = resample_by_distance(df_raw, step_km=0.5)

    df["cum_distance"] -= df["cum_distance"].min()
    df = df.sort_values("cum_distance").reset_index(drop=True)
    df = df.drop_duplicates(subset=["cum_distance"])

    st.session_state["df"] = df

    # ---------- CLASSIFICATION ----------
    def classify_gradient(g):
        g = g * 100
        if g > 15:
            return "Steep"
        elif g > 5:
            return "Uphill"
        elif g < -5:
            return "Downhill"
        else:
            return "Flat"

    df["segment_type"] = df["gradient"].apply(classify_gradient)

    def build_segments(df, step_km=0.5):
        segments = []

        max_km = df["cum_distance"].max()
        current_km = 0

        while current_km < max_km:
            start_km = current_km
            end_km = current_km + step_km

            # 🔥 ALWAYS FIND CLOSEST POINTS
            start_point = df.iloc[(df["cum_distance"] - start_km).abs().argsort()[:1]]
            end_point = df.iloc[(df["cum_distance"] - end_km).abs().argsort()[:1]]

            elev_start = float(start_point["elevation"].values[0])
            elev_end = float(end_point["elevation"].values[0])
            elev_delta = elev_end - elev_start

            # gradient (keep it)
            segment = df[
                (df["cum_distance"] >= start_km) &
                (df["cum_distance"] <= end_km)
            ]

            if len(segment) > 0:
                avg_gradient = segment["gradient"].mean()
            else:
                avg_gradient = 0

            # ---------- CLASSIFICATION ----------
            if elev_delta > 60:
                seg_type = "Steep"
            elif elev_delta > 35:
                seg_type = "Uphill"
            elif elev_delta < -35:
                seg_type = "Downhill"
            else:
                seg_type = "Flat"

            segments.append({
                "type": seg_type,
                "start_km": start_km,
                "end_km": end_km,
                "distance": step_km,
                "elev_delta": elev_delta,
                "avg_gradient": avg_gradient
            })

            current_km += step_km

        return pd.DataFrame(segments)
    

    def merge_same_segments(df):
        if df.empty:
            return df

        merged = []
        current = df.iloc[0].to_dict()

        for i in range(1, len(df)):
            row = df.iloc[i]

            if row["type"] == current["type"]:
                current["end_km"] = row["end_km"]
                current["distance"] += row["distance"]
                current["elev_delta"] += row["elev_delta"]
            else:
                merged.append(current)
                current = row.to_dict()

        merged.append(current)

        return pd.DataFrame(merged)

    # ---------- GROUP ----------
    segments_df = build_segments(df)
    segments_df = merge_same_segments(segments_df)

    if not segments_df.empty:
        segments_df = segments_df[segments_df["distance"] > 0]
        
        # ---------- ELEVATION DELTA ----------
        def get_elevation_delta(start_km, end_km):
            segment = df[
                (df["cum_distance"] >= start_km) &
                (df["cum_distance"] <= end_km)
            ]

            # 🔥 if not enough points → use closest points
            if len(segment) < 2:
                start_point = df.iloc[(df["cum_distance"] - start_km).abs().argsort()[:1]]
                end_point = df.iloc[(df["cum_distance"] - end_km).abs().argsort()[:1]]

                elev_start = float(start_point["elevation"].values[0])
                elev_end = float(end_point["elevation"].values[0])
            else:
                elev_start = segment["elevation"].iloc[0]
                elev_end = segment["elevation"].iloc[-1]

            return elev_end - elev_start

        # ---------- GRADIENT DEG ----------
        segments_df["gradient_deg"] = np.degrees(
            np.arctan(segments_df["elev_delta"] / (segments_df["distance"] * 1000 + 1e-6))
        )

        # ---------- END ELEVATION ----------
        def get_end_elevation(km):
            closest = df.iloc[(df["cum_distance"] - km).abs().argsort()[:1]]
            return float(closest["elevation"].values[0])

        segments_df["end_elevation"] = segments_df["end_km"].apply(get_end_elevation)

    else:
        st.warning("No segments detected")

    st.success("GPX Loaded Successfully")

        # ---------- STATS ----------
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Elevation Gain", int(df["elevation"].diff().clip(lower=0).sum()))
    col2.metric("Max Elevation", int(df["elevation"].max()))

    cutoff_time = col3.number_input(
        "Cut-Off Time (hours)",
        min_value=1.0,
        max_value=24.0,
        value=8.0,
        step=0.5
    )
    st.session_state["segments_df"] = segments_df
    st.session_state["cutoff_time"] = cutoff_time
    # ---------- MAP ----------
    st.subheader("Route Map")
    

    fig_map = go.Figure()

    color_map = {
    "Steep": "#ff4d4f",       # soft red (danger)
    "Uphill": "#ffd966",      # muted amber
    "Flat": "#4da6ff",        # soft cyan
    "Downhill": "#00cc66"     # muted green
    }

    for seg in segments_df.itertuples():

        segment_points = df_raw[
            (df_raw["cum_distance"] >= seg.start_km) &
            (df_raw["cum_distance"] <= seg.end_km)
        ]

        if len(segment_points) < 2:
            continue

        fig_map.add_trace(go.Scattermapbox(
            lat=segment_points["lat"].astype(float),
            lon=segment_points["lon"].astype(float),
            mode="lines",
            line=dict(width=4, color=color_map.get(seg.type, "white")),
            showlegend=False
        ))
 
    if not water_df.empty:
        fig_map.add_trace(go.Scattermapbox(
            lat=water_df["lat"],
            lon=water_df["lon"],
            mode="markers+text",
            marker=dict(
                size=9,
                color="#00b4d8"
            ),
            text=water_df["name"],
            textposition="top center",
            name="WS"
        ))

   
    # 🔥 THIS PART WAS MISSING
    fig_map.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=12.5,
        mapbox_center=dict(
            lat=df_raw["lat"].mean(),
            lon=df_raw["lon"].mean()
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500
    )

    st.plotly_chart(fig_map, use_container_width=True)


    # ---------- ELEVATION ----------
    st.subheader("Elevation Profile")

    fig = go.Figure()

    ws_km = []
    ws_elev = []
    ws_label = []

    for wp in water_df.itertuples():
        closest = df_raw.iloc[
            ((df_raw["lat"] - wp.lat)**2 + (df_raw["lon"] - wp.lon)**2).argsort()[:1]
        ]

        km = float(closest["cum_distance"].values[0])

        elev_point = df.iloc[(df["cum_distance"] - km).abs().argsort()[:1]]

        ws_km.append(km)
        ws_elev.append(float(elev_point["elevation"].values[0]))
        ws_label.append(wp.name)

    fig.add_trace(go.Scatter(
        x=ws_km,
        y=ws_elev,
        mode="markers+text",
        marker=dict(size=7, color="#00b4d8"),
        text=ws_label,
        textposition="top center",
        name="Water Station"
    ))

    fig.add_trace(go.Scatter(
        x=df["cum_distance"],
        y=df["elevation"],
        mode="lines",
        line=dict(color="white", width=2),
        fill="tozeroy",  # 🔥 THIS ADDS AREA
        fillcolor="rgba(100, 150, 255, 0.3)"  # soft blue
    ))

    fig.update_layout(
        xaxis_title="Distance (KM)",
        yaxis_title="Elevation (m)",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


    # ---------- DISPLAY ----------
    st.subheader("Tactical Strategy")

    def color_rows(row):
        color_map = {
            "Steep": "color: red;",
            "Uphill": "color: #ffd966;",
            "Flat": "color: #4da6ff;",
            "Downhill": "color: #00cc66;"
        }

        style = color_map.get(row["Type"], "")
        return [style] * len(row)
       
    display_df = segments_df.copy()

    # format (2 decimal)
    display_df["KM Start"] = display_df["start_km"].map(lambda x: f"{x:.2f}".rstrip("0").rstrip("."))
    display_df["KM End"] = display_df["end_km"].map(lambda x: f"{x:.2f}".rstrip("0").rstrip("."))
    display_df["Distance (KM)"] = display_df["distance"].map(lambda x: f"{x:.2f}")
    display_df["Gradient (°)"] = display_df["gradient_deg"].map(lambda x: f"{x:.2f}")
    display_df["Elevation Δ (m)"] = display_df["elev_delta"].map(lambda x: f"{x:.2f}")
    display_df["Elevation (m)"] = display_df["end_elevation"].map(lambda x: f"{x:.2f}")

    display_df = display_df.rename(columns={"type": "Type"})

    display_df = display_df[[
        "Type",
        "KM Start",
        "KM End",
        "Distance (KM)",
        "Gradient (°)",
        "Elevation Δ (m)",
        "Elevation (m)"
    ]]

    # ---------- SAFE COLORING (NO STYLER CRASH) ----------
    def get_color(val):
        return {
            "Steep": "red",
            "Uphill": "#ffd966",
            "Flat": "#4da6ff",
            "Downhill": "#00cc66"
        }.get(val, "white")

    # convert Type column to colored text manually
    st.dataframe(
        display_df.style.apply(color_rows, axis=1),
        use_container_width=True
    )

    # ---------- FUEL ----------
    st.subheader("Fuel Plan")

    fuel_rows = []
    for seg in segments_df.itertuples():
        if seg.type in ["Steep", "Uphill"]:
            action = "Gel BEFORE"
        elif seg.type == "Flat":
            action = "Optional"
        else:
            action = "Hydrate"

        fuel_rows.append({
            "KM": round(seg.start_km, 1),
            "Segment": seg.type,
            "Action": action
        })

    st.dataframe(pd.DataFrame(fuel_rows), use_container_width=True)

    # ---------- DANGER ----------
    st.subheader("⚠️Danger Zones")

    danger = segments_df[
        (segments_df["type"] == "Steep") &
        (segments_df["distance"] > 1)
    ]

    if not danger.empty:
        for d in danger.itertuples():
            st.error(f"KM {round(d.start_km,1)}–{round(d.end_km,1)} → Long steep climb")
    else:
        st.success("No major danger zones detected")

else:
    st.info("Upload a GPX file to begin")