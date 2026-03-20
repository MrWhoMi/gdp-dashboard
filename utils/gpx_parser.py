import gpxpy
import pandas as pd
import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    return R * c

def parse_gpx(file):
    gpx = gpxpy.parse(file)

    points = []
    waypoints = []  # 🔥 NEW

    # ---------- TRACK POINTS ----------
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append({
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "elevation": point.elevation
                })

    df = pd.DataFrame(points)

    # ---------- DISTANCE CALC ----------
    distances = [0]

    for i in range(1, len(df)):
        d = haversine(
            df.loc[i-1, "lat"], df.loc[i-1, "lon"],
            df.loc[i, "lat"], df.loc[i, "lon"]
        )
        distances.append(d)

    df["segment_km"] = distances
    df["cum_distance"] = df["segment_km"].cumsum()

    # ---------- GRADIENT ----------
    df["elev_diff"] = df["elevation"].diff()
    df["gradient"] = df["elev_diff"] / (df["segment_km"] * 1000)
    df["gradient"] = df["gradient"].fillna(0)

    # ---------- 🔥 WAYPOINTS ----------
    for wp in gpx.waypoints:
        waypoints.append({
            "lat": wp.latitude,
            "lon": wp.longitude,
            "elevation": wp.elevation,
            "name": wp.name,
            "symbol": wp.symbol,
            "type": wp.type
        })

    wp_df = pd.DataFrame(waypoints)

    return df, wp_df  # 🔥 CHANGED

def group_segments(df):
    segments = []

    current_type = df.loc[0, "segment_type"]
    start_idx = 0

    for i in range(1, len(df)):
        if df.loc[i, "segment_type"] != current_type:

            segment = df.iloc[start_idx:i]

            segments.append({
                "type": current_type,
                "start_km": segment["cum_distance"].iloc[0],
                "end_km": segment["cum_distance"].iloc[-1],
                "distance": segment["cum_distance"].iloc[-1] - segment["cum_distance"].iloc[0],
                "avg_gradient": segment["gradient"].mean()
            })

            current_type = df.loc[i, "segment_type"]
            start_idx = i

    # ✅ ADD LAST SEGMENT
    segment = df.iloc[start_idx:]
    segments.append({
        "type": current_type,
        "start_km": segment["cum_distance"].iloc[0],
        "end_km": segment["cum_distance"].iloc[-1],
        "distance": segment["cum_distance"].iloc[-1] - segment["cum_distance"].iloc[0],
        "avg_gradient": segment["gradient"].mean()
    })

    return pd.DataFrame(segments)

def resample_by_distance(df, step_km=0.5):
    bins = np.arange(0, df["cum_distance"].max(), step_km)
    df["bin"] = np.digitize(df["cum_distance"], bins)

    grouped = df.groupby("bin").agg({
        "cum_distance": "mean",
        "elevation": "mean",
        "gradient": "mean"
    }).reset_index(drop=True)

    return grouped

def merge_small_segments(df, min_km=0.3):
    merged = []

    buffer = df.iloc[0].to_dict()

    for i in range(1, len(df)):
        row = df.iloc[i]

        # If too small → merge
        if buffer["distance"] < min_km:
            buffer["end_km"] = row["end_km"]
            buffer["distance"] = buffer["end_km"] - buffer["start_km"]
            buffer["avg_gradient"] = (buffer["avg_gradient"] + row["avg_gradient"]) / 2
        else:
            merged.append(buffer)
            buffer = row.to_dict()

    merged.append(buffer)

    return pd.DataFrame(merged)
