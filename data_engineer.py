#data_engineer.py

import logging
import pandas as pd

from helperfunctions import (assignRunIds, computeProcessMetrics, computeTotals, computeStageAggregates, computeCleaningHistory, _window_slice, _last_hours_slice, _safe_slope)

logging.basicConfig(level=logging.INFO)

class DataEngineer:
    def transform(self, df_states, df_sysdata, df_stagedata, last_ts=None):
        df_states.rename(columns={'EndTime': 'Timestamp'}, inplace=True)
        if df_states.empty:
            return None

        runs_df, progsummarydf = computeProcessMetrics(assignRunIds(df_states))
        totals_df = computeTotals(df_sysdata[['Timestamp', 'MAIN_TOTAL']], runs_df)

        final_rows = []

        for _, run in runs_df.iterrows():
            if last_ts is not None and run["production_start_ts"] <= last_ts:
                continue
            row = run.to_dict()

            # --Totals--
            trow = totals_df[totals_df["RunId"] == run["RunId"]]
            if not trow.empty:
                trow = trow.iloc[0]
                row["total_lbs_produced"] = (trow["total_lbs_produced"] if pd.notna(trow["total_lbs_produced"]) else 0)
                row["avg_lbs_per_hr"] = (trow["avg_lbs_per_hr"] if pd.notna(trow["avg_lbs_per_hr"]) else 0)
                if pd.notna(trow["max_lbs_per_hr"]) and trow["max_lbs_per_hr"] != 0:
                    row["lbs_per_hr_normalized"] = (trow["avg_lbs_per_hr"] / trow["max_lbs_per_hr"])
                else:
                    row["lbs_per_hr_normalized"] = 0

            # --Stage Features--
            stage_slice = _window_slice(df_stagedata, run["production_start_ts"], run["production_end_ts"])
            row.update(computeStageAggregates(stage_slice))

            # --ProSpect Slopes--
            pro_slice = _last_hours_slice(_window_slice(df_sysdata[['Timestamp', 'PDB', 'Protein', 'Solids']], run["production_start_ts"], run["production_end_ts"]), run["production_end_ts"], 6)
            slope_map = {
                            "PDB": "pdb_slope_last_6h",
                            "Protein": "protein_slope_last_6h",
                            "Solids": "solids_slope_last_6h"
                        }
            for col, name in slope_map.items():
                if col in pro_slice.columns:
                    row[name] = _safe_slope(pro_slice[col], pro_slice["Timestamp"])

            # --Cleaning History--
            row.update(computeCleaningHistory(run, progsummarydf))

            final_rows.append(row)

        if not final_rows:
            return None
        
        return pd.DataFrame(final_rows)