#helperfunctions.py

import os
import numpy as np
import pandas as pd
import pyodbc
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)


def _window_slice(df, start, end):
    return df[(df["Timestamp"] >= start) & (df["Timestamp"] <= end)].copy()

def _last_hours_slice(df, end, hours):
    start = end - pd.Timedelta(hours=hours)
    return df[(df["Timestamp"] >= start) & (df["Timestamp"] <= end)].copy()

def _safe_slope(s, ts):
    s = pd.to_numeric(s, errors="coerce")
    ts = pd.to_datetime(ts, errors="coerce")
    if len(s) < 2:
        return None
    x = (ts - ts.iloc[0]).dt.total_seconds().values
    y = s.values
    if np.all(x == 0):
        return None
    return np.polyfit(x, y, 1)[0]

def _safe_ratio(series):
    if series.empty:
        return None
    smin = series.min()
    smax = series.max()
    if pd.isna(smin) or smin == 0:
        return None
    return smax / smin


def assignRunIds(df):
    # dfnz = df[df['Program_Loaded'] != 0].copy()
    dfnz = df.copy()
    runStart = ((dfnz['Program_Loaded'] == 1) & (dfnz['Program_Loaded'].shift(fill_value=1) != 1))
    dfnz.loc[runStart, 'RunId'] = (pd.to_datetime(dfnz.loc[runStart, 'Timestamp']).dt.strftime("%y%m%d%H%M"))
    df = df.merge(dfnz[['Timestamp', 'RunId']],on='Timestamp', how='left')
    df['RunId'] = df['RunId'].ffill().astype("Int64")
    df = df[df['RunId'].notna()]  
    df['RunId'] = df['RunId'].astype(str)
    return df


def computeProcessMetrics(df):
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df["StartTime"] = pd.to_datetime(df["StartTime"])

    program_map = {
                        1: "Process",
                        2: "CIP",
                        3: "Sanitize",
                        4: "Rinse",
                        5: "Soak",
                        6: "Short_CIP"
                  }

    runs = []
    summaries = []

    for runid, grp in df.groupby("RunId"):
        grp = grp.sort_values("Timestamp")
        row = {"RunId": runid}

        for code, name in program_map.items():
            prog = grp[grp["Program_Loaded"] == code]
            if not prog.empty:
                start = prog["StartTime"].min()
                end = prog["Timestamp"].max()
                dur = (end - start).total_seconds() / 60
            else:
                start = end = pd.NaT
                dur = np.nan
            row[f"{name}_DurMin"] = dur
            row[f"{name}_End"] = end

        summaries.append(row)

        prod = grp[(grp["Program_Loaded"] == 1) & (grp["Step_Number"] == 4)]
        if not prod.empty:
            row_prod = prod.iloc[0] 
            pstart = row_prod["StartTime"]
            pend = row_prod["Timestamp"]
            dur_min = (pend - pstart).total_seconds() / 60
            dur_hr = dur_min / 60
        else:
            pstart = pend = dur_min = dur_hr = None
            # continue
        runs.append({
                        "RunId": runid,
                        "production_start_ts": pstart,
                        "production_end_ts": pend,
                        "duration_min": dur_min,
                        "duration_hr": dur_hr
                    })
    return pd.DataFrame(runs), pd.DataFrame(summaries)


def computeTotals(ufdf, proddf):
    ufdf["Timestamp"] = pd.to_datetime(ufdf["Timestamp"])
    out = []
    for _, r in proddf.iterrows():
        mask = ((ufdf["Timestamp"] >= r["production_start_ts"]) & (ufdf["Timestamp"] <= r["production_end_ts"]))
        run_uf = ufdf.loc[mask].sort_values("Timestamp")
        if len(run_uf) < 2 or not r["duration_hr"]:
            out.append({
                            "RunId": r["RunId"],
                            "total_lbs_produced": None,
                            "avg_lbs_per_hr": None,
                            "max_lbs_per_hr": None
                        })
            continue
        dt_hr = run_uf["Timestamp"].diff().dt.total_seconds() / 3600
        diff = run_uf["MAIN_TOTAL"].diff()
        pos = diff[(diff > 0) & (dt_hr > 0)]
        total = pos.sum()
        max_hr = (pos / dt_hr[pos.index]).max()
        out.append({
                        "RunId": r["RunId"],
                        "total_lbs_produced": total,
                        "avg_lbs_per_hr": total / r["duration_hr"],
                        "max_lbs_per_hr": max_hr
                    })

    return pd.DataFrame(out)


def computeStageAggregates(run_df):
    if run_df.empty:
        return {}

    end = run_df["Timestamp"].max()
    last2h = _last_hours_slice(run_df, end, 2)
    last6h = _last_hours_slice(run_df, end, 6)

    pivot_tmp = last2h.pivot(index="Timestamp", columns="Stage", values="TransmembranePressure")
    pivot_pd = last2h.pivot(index="Timestamp", columns="Stage", values="PressureDrop")
    pivot_flow = last2h.pivot(index="Timestamp", columns="Stage", values="PermeateFlowRate")

    out = {}
    out["tmp_mean_last_2h_across_stages"] = pivot_tmp.mean().mean()
    out["tmp_std_last_2h_across_stages"] = pivot_tmp.std().mean()
    out["pressure_drop_std_last_2h_across_stages"] = pivot_pd.std().mean()

    out["max_tmp_stage_last_2h"] = pivot_tmp.mean().idxmax()
    out["max_pressure_drop_stage_last_2h"] = pivot_pd.mean().idxmax()
    out["min_permeate_flow_stage_last_2h"] = pivot_flow.mean().idxmin()

    out["tmp_max_to_min_ratio_last_2h"] = _safe_ratio(pivot_tmp.mean())

    out["pressure_drop_max_to_min_ratio_last_2h"] = _safe_ratio(pivot_pd.mean())

    # --Slopes--
    tmp_slopes = []
    pd_slopes = []
    flow_slopes = []

    for stage in last6h["Stage"].dropna().unique():
        sdf = last6h[last6h["Stage"] == stage]
        tmp_slopes.append(_safe_slope(sdf["TransmembranePressure"], sdf["Timestamp"]))
        pd_slopes.append(_safe_slope(sdf["PressureDrop"], sdf["Timestamp"]))
        flow_slopes.append(_safe_slope(sdf["PermeateFlowRate"], sdf["Timestamp"]))

    tmp_slopes = [x for x in tmp_slopes if x is not None]
    pd_slopes = [x for x in pd_slopes if x is not None]
    flow_slopes = [x for x in flow_slopes if x is not None]

    out["max_tmp_slope_last_6h"] = max(tmp_slopes) if tmp_slopes else None
    out["mean_tmp_slope_last_6h"] = np.mean(tmp_slopes) if tmp_slopes else None

    out["max_pressure_drop_slope_last_6h"] = max(pd_slopes) if pd_slopes else None
    out["mean_pressure_drop_slope_last_6h"] = np.mean(pd_slopes) if pd_slopes else None

    out["min_permeate_flow_slope_last_6h"] = min(flow_slopes) if flow_slopes else None

    tmp_p90 = run_df["TransmembranePressure"].quantile(0.9)
    pd_p90 = run_df["PressureDrop"].quantile(0.9)

    out["minutes_tmp_above_p90"] = (run_df["TransmembranePressure"] > tmp_p90).sum()
    out["minutes_pressure_drop_above_p90"] = (run_df["PressureDrop"] > pd_p90).sum()

    return out


def computeCleaningHistory(current_run, progsummarydf, chkprevdur):
    prev = progsummarydf[progsummarydf["RunId"] < current_run["RunId"]] 
    if prev.empty:
        return {}
    last = prev.iloc[-1] if not pd.isna(chkprevdur) else prev.iloc[-2]

    out = {}
    clean_cols = ["CIP_DurMin", "Short_CIP_DurMin", "Soak_DurMin", "Sanitize_DurMin", "Rinse_DurMin"]
    
    # --Total cleaning time--
    clean_vals = (last[clean_cols].apply(pd.to_numeric, errors="coerce").fillna(0))
    for col in clean_cols:
        out[f"{col}_last_cycle"] = clean_vals[col]
    out["total_cleaning_minutes_last_cycle"] = clean_vals.sum()

    # --Flags--
    out["had_cip_last_cycle"] = int(clean_vals["CIP_DurMin"] > 0)
    out["had_rinse_last_cycle"] = int(clean_vals["Rinse_DurMin"] > 0)
    out["had_shortcip_last_cycle"] = int(clean_vals["Short_CIP_DurMin"] > 0)
    out["had_soak_last_cycle"] = int(clean_vals["Soak_DurMin"] > 0)
    out["had_sanitize_last_cycle"] = int(clean_vals["Sanitize_DurMin"] > 0)

    # --Time since last full CIP--
    last_full = prev[prev["CIP_DurMin"] > 0]
    if not last_full.empty:
        last_cip_end = last_full.iloc[-1]["CIP_End"]
        if pd.notna(last_cip_end):
            out["time_since_last_full_CIP"] = ((current_run["production_end_ts"] - last_cip_end).total_seconds() / 3600)

    return out