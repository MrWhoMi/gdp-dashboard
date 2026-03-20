import gpxpy
import pandas as pd
import numpy as np

def fix_segment_gaps(df, segments_df):
        fixed = []

        prev_end = 0.0

        for seg in segments_df.itertuples():
            start = seg.start_km
            end = seg.end_km

            # 🔥 Fill gap if exists
            if start > prev_end:
                fixed.append({
                    "type": "Flat",
                    "start_km": prev_end,
                    "end_km": start,
                    "distance": start - prev_end,
                    "avg_gradient": 0
                })

            fixed.append({
                "type": seg.type,
                "start_km": start,
                "end_km": end,
                "distance": end - start,
                "avg_gradient": seg.avg_gradient
            })

            prev_end = end

        # 🔥 Ensure starts from 0
        if fixed and fixed[0]["start_km"] > 0:
            fixed.insert(0, {
                "type": "Flat",
                "start_km": 0,
                "end_km": fixed[0]["start_km"],
                "distance": fixed[0]["start_km"],
                "avg_gradient": 0
            })

        return pd.DataFrame(fixed)

