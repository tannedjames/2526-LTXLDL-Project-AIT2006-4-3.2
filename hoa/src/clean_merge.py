# -*- coding: utf-8 -*-
"""
Clean, standardize, resample (daily), and merge Weather + Air Quality data.

Inputs (must exist):
  raw/weather.csv        (Meteostat daily; has 'date', not 'timestamp')
  raw/air_quality.csv    (Open-Meteo style; metadata lines + header line with 'time,...')

Outputs (overwritten if exist):
  processed/clean_data.csv
  reports/qa_summary.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np
import re

# ---------------------------
# 1) PATHS (anchored to repo root)
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
PROC_DIR = BASE_DIR / "processed"
REPORT_DIR = BASE_DIR / "reports"
FIG_DIR = BASE_DIR / "figures"

for d in [PROC_DIR, REPORT_DIR, FIG_DIR]:
    d.mkdir(exist_ok=True, parents=True)

# ---------------------------
# 2) CONFIG
# ---------------------------
LOCAL_TZ = "Asia/Bangkok"  # matches your file metadata
# Validation ranges (units noted)
RANGE = {
    "temperature": (-50, 60),   # °C
    "rain": (0, 500),           # mm/day
    "wind_speed": (0, 60),      # m/s (we'll convert Meteostat km/h -> m/s)
    "pressure": (870, 1085),    # hPa
    "pm25": (0, 1000),          # µg/m³
    "pm10": (0, 1000),          # µg/m³
    "uv_index": (0, 15),        # dimensionless
}

# ---------------------------
# 3) READERS (handle metadata + flexible time columns)
# ---------------------------
def _find_header_start(path: Path) -> int:
    """
    Scan file and return the 0-based line index where the real header begins.
    We look for a line starting with 'time,' or 'date,' (case-insensitive).
    If not found, return 0.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for i, line in enumerate(lines[:50]):  # first 50 lines is plenty
        s = line.strip().lower()
        if s.startswith("time,") or s.startswith("date,"):
            return i
    return 0

def read_csv_flexible_time(path: Path) -> pd.DataFrame:
    """
    Read CSV that may have metadata lines before the header,
    and whose time column could be 'timestamp'/'time'/'datetime' or 'date'.
    """
    skip = _find_header_start(path)
    df = pd.read_csv(path, skiprows=skip)
    # Normalize a time column to 'timestamp'
    time_col = None
    for col in df.columns:
        lc = col.lower().strip()
        if lc in ["timestamp", "time", "datetime", "date"]:
            time_col = col
            break
    if time_col is None:
        raise ValueError(f"Missing time column ('timestamp'/'time'/'datetime' or 'date') in {path}")

    if time_col.lower() in ["timestamp", "time", "datetime"]:
        # Assume values are either ISO w/ TZ or local-naive. We'll parse naive and localize.
        ts = pd.to_datetime(df[time_col], errors="coerce")
        df = df.loc[ts.notna()].copy()
        # If timezone-aware already, convert; else, localize to LOCAL_TZ
        if hasattr(ts.dt, "tz") and ts.dt.tz is not None:
            df["timestamp"] = ts.dt.tz_convert(LOCAL_TZ)
        else:
            df["timestamp"] = ts.dt.tz_localize(LOCAL_TZ)
    else:
        # Daily date-only column
        d = pd.to_datetime(df[time_col], errors="coerce").dt.normalize()
        df = df.loc[d.notna()].copy()
        df["timestamp"] = d.dt.tz_localize(LOCAL_TZ)

    # Deduplicate & sort
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df

# ---------------------------
# 4) COLUMN NORMALIZATION
# ---------------------------
def _slugify_col(name: str) -> str:
    """
    Lowercase, remove units in parentheses, collapse to snake_case ascii-ish.
    E.g. 'pm10 (μg/m³)' -> 'pm10'; 'carbon_dioxide (ppm)' -> 'carbon_dioxide'
    """
    base = name.strip().lower()
    base = re.sub(r"\(.*?\)", "", base)        # remove unit parentheses
    base = base.replace("µ", "u").replace("μ", "u")  # normalize micro symbol
    base = re.sub(r"[^a-z0-9]+", "_", base)    # non-alnum -> underscore
    base = re.sub(r"_+", "_", base).strip("_") # collapse underscores
    return base

def normalize_air_columns(air: pd.DataFrame) -> pd.DataFrame:
    # Clean/simplify noisy names
    rename = {}
    for c in air.columns:
        if c == "timestamp":  # keep our normalized time col
            continue
        s = _slugify_col(c)
        # Canonicalize known pollutants / fields
        if s in ["pm10"]:
            rename[c] = "pm10"
        elif s in ["pm2_5", "pm25", "pm2_5_ug_m3", "pm25_ug_m3"]:
            rename[c] = "pm25"
        elif s in ["ozone", "o3"]:
            rename[c] = "ozone"
        elif s in ["sulphur_dioxide", "sulfur_dioxide", "so2"]:
            rename[c] = "so2"
        elif s in ["nitrogen_dioxide", "no2"]:
            rename[c] = "no2"
        elif s in ["carbon_dioxide", "co2"]:
            rename[c] = "co2"
        elif s in ["carbon_monoxide", "co"]:
            rename[c] = "co"
        elif s in ["uv_index", "uv_index_clear_sky"]:  # keep both if both exist
            rename[c] = s
        elif s in ["aerosol_optical_depth", "aod"]:
            rename[c] = "aod"
        elif s in ["dust"]:
            rename[c] = "dust"
        elif s in ["methane", "ch4"]:
            rename[c] = "ch4"
        else:
            # keep normalized token for transparency
            rename[c] = s
    air = air.rename(columns=rename)
    return air

def normalize_weather_columns(weather: pd.DataFrame) -> pd.DataFrame:
    # Meteostat daily columns:
    # date,tavg,tmin,tmax,prcp,snow,wdir,wspd,wpgt,pres,tsun
    weather = weather.rename(columns={
        "tavg": "temperature",  # °C (daily avg)
        "tmin": "temp_min",
        "tmax": "temp_max",
        "prcp": "rain",         # mm
        "snow": "snow",         # mm
        "wdir": "wind_dir",     # °
        "wspd": "wind_speed",   # km/h (convert below)
        "wpgt": "wind_gust",    # km/h (convert below)
        "pres": "pressure",     # hPa
        "tsun": "sunshine"      # s
    })
    # Convert wind from km/h -> m/s to match RANGE
    if "wind_speed" in weather.columns:
        weather["wind_speed"] = weather["wind_speed"] / 3.6
    if "wind_gust" in weather.columns:
        weather["wind_gust"] = weather["wind_gust"] / 3.6
    return weather

# ---------------------------
# 5) CLEANING HELPERS
# ---------------------------
def _flag_and_mask(df: pd.DataFrame, col: str, lo: float, hi: float) -> pd.Series:
    if col not in df.columns:
        return pd.Series(pd.NA, index=df.index)
    bad = (df[col] < lo) | (df[col] > hi)
    if lo >= 0:
        bad |= df[col] < 0
    df.loc[bad, col] = np.nan
    df[f"{col}_flag"] = np.where(bad, "error", "ok")
    return df[f"{col}_flag"]

def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    _flag_and_mask(out, "rain", *RANGE["rain"])
    _flag_and_mask(out, "wind_speed", *RANGE["wind_speed"])
    _flag_and_mask(out, "pressure", *RANGE["pressure"])
    _flag_and_mask(out, "temperature", *RANGE["temperature"])
    return out

def clean_air(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    _flag_and_mask(out, "pm25", *RANGE["pm25"])
    _flag_and_mask(out, "pm10", *RANGE["pm10"])
    # Logic warning: pm25 shouldn't exceed pm10 (when both valid)
    if {"pm25", "pm10"}.issubset(out.columns):
        warn = out["pm25"].notna() & out["pm10"].notna() & (out["pm25"] > out["pm10"])
        if "pm25_flag" not in out:
            out["pm25_flag"] = "ok"
        out.loc[warn, "pm25_flag"] = "logic_warn"
    return out

def resample_daily_mean(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.set_index("timestamp")
          .sort_index()
          .resample("D")
          .mean(numeric_only=True)
          .rename_axis("date")
          .reset_index()
    )

# ---------------------------
# 6) QA SUMMARY
# ---------------------------
def build_qa_summary(weather_raw, air_raw, weather_daily, air_daily, merged) -> pd.DataFrame:
    def cnt(df, col, val):
        return int((df[col] == val).sum()) if col in df.columns else 0
    qa = {
        "rain_error_count":        cnt(weather_raw, "rain_flag", "error"),
        "wind_error_count":        cnt(weather_raw, "wind_speed_flag", "error"),
        "pressure_error_count":    cnt(weather_raw, "pressure_flag", "error"),
        "temperature_error_count": cnt(weather_raw, "temperature_flag", "error"),
        "pm25_error_count":        cnt(air_raw, "pm25_flag", "error"),
        "pm10_error_count":        cnt(air_raw, "pm10_flag", "error"),
        "pm25_logic_warn_count":   cnt(air_raw, "pm25_flag", "logic_warn"),
        "weather_hourly_records":  int(len(weather_raw)),
        "air_hourly_records":      int(len(air_raw)),
        "weather_daily_days":      int(weather_daily["date"].nunique()),
        "air_daily_days":          int(air_daily["date"].nunique()),
        "total_days_merged":       int(len(merged)),
    }
    return pd.DataFrame([qa])

# ---------------------------
# 7) MAIN
# ---------------------------
def main():
    # Load
    weather = read_csv_flexible_time(RAW_DIR / "weather.csv")
    air     = read_csv_flexible_time(RAW_DIR / "air_quality.csv")

    # Normalize names/units
    weather = normalize_weather_columns(weather)
    air     = normalize_air_columns(air)

    # Clean
    weather_clean = clean_weather(weather)
    air_clean     = clean_air(air)

    # Daily resample (no-op for already-daily inputs)
    weather_daily = resample_daily_mean(weather_clean)
    air_daily     = resample_daily_mean(air_clean)

    # Merge on date (inner keeps shared days only)
    merged = pd.merge(weather_daily, air_daily, on="date", how="inner")

    # QA summary
    qa_summary = build_qa_summary(weather_clean, air_clean, weather_daily, air_daily, merged)
    qa_summary.to_csv(REPORT_DIR / "qa_summary.csv", index=False)

    # Save merged
    merged.to_csv(PROC_DIR / "clean_data.csv", index=False)

    print("✅ Saved:", REPORT_DIR / "qa_summary.csv")
    print("✅ Saved:", PROC_DIR / "clean_data.csv")

# ---------------------------
# 8) RUN
# ---------------------------
if __name__ == "__main__":
    main()
