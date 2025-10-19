import os
import re
import math
from glob import glob

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
DATA_DIR = "."           # script sits next to Meds/ and NoMeds/
PLOTS_DIR = "plots"
ADV_DIR = os.path.join(PLOTS_DIR, "advanced")

# =========================
# UTILITIES
# =========================
def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(ADV_DIR, exist_ok=True)

def parse_duration(val: str) -> int:
    """
    Parse durations like "1m 23s", "1m 23", "45s", "3m", "0s" into integer seconds.
    """
    if pd.isna(val):
        return 0
    s = str(val).strip().lower().replace("sec", "s")
    s = s.replace("seconds", "s").replace("second", "s").replace("mins", "m").replace("min", "m")
    s = s.replace(" ", "")
    if s == "" or s == "0" or s == "s":
        return 0
    # Accept "XmYs", "XmY", "Xm", "Ys"
    m = re.match(r"^(?:(\d+)m)?(?:(\d+)s?)?$", s)
    if not m:
        # Try a plain integer (seconds)
        try:
            return int(re.sub(r"\D", "", s))
        except:
            return 0
    mins = int(m.group(1)) if m.group(1) else 0
    secs = int(m.group(2)) if m.group(2) else 0
    return mins * 60 + secs

def parse_hms_to_seconds(hms: str) -> int:
    """
    Parse HH:MM:SS to total seconds from video start.
    """
    h, m, s = [int(x) for x in hms.strip().split(":")]
    return h * 3600 + m * 60 + s

def load_day_csv(csv_path: str) -> pd.DataFrame:
    """
    Load a single *_wheel_times.csv as written by your generator.
    Returns a DataFrame with columns: start_sec, end_sec, duration_seconds, state, date
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower()
    # expected: start_time, end_time, state, duration
    if not {"start_time", "end_time", "state", "duration"}.issubset(df.columns):
        raise ValueError(f"Unexpected columns in {csv_path}: {list(df.columns)}")

    df["start_sec"] = df["start_time"].apply(parse_hms_to_seconds)
    df["end_sec"] = df["end_time"].apply(parse_hms_to_seconds)
    df["duration_seconds"] = df["duration"].apply(parse_duration)
    return df[["start_sec", "end_sec", "duration_seconds", "state"]].copy()

def seconds_to_hhmm(x: float) -> str:
    x = int(round(x))
    h = x // 3600
    m = (x % 3600) // 60
    return f"{h:02d}:{m:02d}"

def add_interval_to_hour_bins(start_s: int, dur_s: int, hour_bins: np.ndarray):
    """
    Add 'dur_s' seconds starting at 'start_s' into hour bins of size 3600.
    Splits across hour boundaries properly.
    """
    remaining = dur_s
    cur = start_s
    while remaining > 0:
        hour_index = cur // 3600
        hour_start = hour_index * 3600
        hour_end = hour_start + 3600
        spill = min(remaining, hour_end - cur)
        if hour_index < len(hour_bins):
            hour_bins[hour_index] += spill
        remaining -= spill
        cur += spill

def process_folder(folder_path: str):
    """
    Process all CSVs in a folder (Meds or NoMeds).
    Returns:
      daily_summary: per-day totals/avg/episodes
      sessions_all: all IN WHEEL rows across days
      hourly_long: long format per day per hour active seconds
      max_video_seconds: maximum end_sec across all files (for x-limits)
    """
    csv_files = sorted(glob(os.path.join(folder_path, "*_wheel_times.csv")))
    if not csv_files:
        print(f"⚠️ No CSV files in {folder_path}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0

    daily_rows = []
    sessions_all = []
    hourly_rows = []

    max_video_seconds = 0

    for csv_path in csv_files:
        date = os.path.basename(csv_path).split("_")[0]
        df = load_day_csv(csv_path)

        # Only IN WHEEL episodes; this matches your summary logic
        in_wheel = df[df["state"].str.upper() == "IN WHEEL"].copy()

        # Totals for this day
        total_s = int(in_wheel["duration_seconds"].sum())
        episodes = int(len(in_wheel))
        avg_ep = float(in_wheel["duration_seconds"].mean()) if episodes > 0 else 0.0
        longest = int(in_wheel["duration_seconds"].max()) if episodes > 0 else 0

        # Track the max video length across all days in this condition
        day_max_end = int(df["end_sec"].max()) if not df.empty else 0
        if day_max_end > max_video_seconds:
            max_video_seconds = day_max_end

        daily_rows.append({
            "date": date,
            "total_running_time_s": total_s,
            "total_running_time_min": total_s / 60.0,
            "episodes": episodes,
            "avg_episode_duration_s": avg_ep,
            "longest_episode_s": longest
        })

        if not in_wheel.empty:
            tmp = in_wheel.copy()
            tmp["date"] = date
            sessions_all.append(tmp)

    daily_summary = pd.DataFrame(daily_rows).sort_values("date")
    sessions_df = pd.concat(sessions_all, ignore_index=True) if sessions_all else pd.DataFrame()

    # Build hourly bins per day (0..H-1, H = ceil(max_video_seconds/3600) per condition)
    hours_count = max(1, math.ceil(max_video_seconds / 3600))  # Option A: stop at longest
    for csv_path in csv_files:
        date = os.path.basename(csv_path).split("_")[0]
        df = load_day_csv(csv_path)
        in_wheel = df[df["state"].str.upper() == "IN WHEEL"].copy()

        bins = np.zeros(hours_count, dtype=np.int64)
        for _, row in in_wheel.iterrows():
            start = int(row["start_sec"])
            dur = int(row["duration_seconds"])
            add_interval_to_hour_bins(start, dur, bins)

        for hr in range(hours_count):
            hourly_rows.append({
                "date": date,
                "hour": hr,
                "active_seconds": int(bins[hr])
            })

    hourly_long = pd.DataFrame(hourly_rows).sort_values(["date", "hour"])
    return daily_summary, sessions_df, hourly_long, max_video_seconds

def avg_cumulative_curve(sessions_df: pd.DataFrame, max_seconds: int, step: int = 60) -> pd.DataFrame:
    """
    Build an average cumulative active-time curve over [0..max_seconds], sampled every 'step' seconds.
    For each day, we accumulate all IN WHEEL durations along the timeline, then average across days.
    """
    if sessions_df.empty:
        return pd.DataFrame(columns=["t_sec", "avg_cum_sec"])

    # Extract per-day sessions
    by_day = {}
    for date, group in sessions_df.groupby("date"):
        # Build a per-second (or per-step) cumulative array
        t_samples = np.arange(0, max_seconds + step, step)
        active = np.zeros_like(t_samples, dtype=np.int64)

        # Fill active seconds into the step grid
        for _, row in group.iterrows():
            start = int(row["start_sec"])
            dur = int(row["duration_seconds"])
            end = min(max_seconds, start + dur)
            if end <= start:
                continue
            # Convert to indices in the step grid
            s_idx = start // step
            e_idx = end // step
            # Add within bins; approximate by adding full step coverage
            # For better precision, proportionally split edges, but this is enough at 60s resolution
            active[s_idx:e_idx] += step

        cum = np.cumsum(active)
        by_day[date] = cum

    # Average across days
    all_curves = np.stack(list(by_day.values()), axis=0)  # [days, timepoints]
    avg_curve = all_curves.mean(axis=0)
    return pd.DataFrame({"t_sec": np.arange(0, max_seconds + step, step), "avg_cum_sec": avg_curve})

# =========================
# PLOTTING
# =========================
def plot_daily_totals(df_meds, df_nomeds):
    plt.figure(figsize=(12, 6))
    plt.plot(df_meds["date"], df_meds["total_running_time_min"], marker="o", label="Meds")
    plt.plot(df_nomeds["date"], df_nomeds["total_running_time_min"], marker="o", label="No Meds")
    plt.xticks(rotation=45)
    plt.ylabel("Total Running Time (min)")
    plt.title("Daily Total Wheel Running Time")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "daily_running_time.png"))

def plot_avg_episode_duration(df_meds, df_nomeds):
    plt.figure(figsize=(12, 6))
    index = np.arange(len(df_meds))
    # Align by date; simpler approach: plot side-by-side by category using date strings
    plt.bar(df_meds["date"], df_meds["avg_episode_duration_s"], alpha=0.7, label="Meds")
    plt.bar(df_nomeds["date"], df_nomeds["avg_episode_duration_s"], alpha=0.7, label="No Meds")
    plt.xticks(rotation=45)
    plt.ylabel("Average Episode Duration (s)")
    plt.title("Average Episode Duration per Day")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "avg_episode_duration.png"))

def plot_episodes_per_day(df_meds, df_nomeds):
    plt.figure(figsize=(12, 6))
    plt.bar(df_meds["date"], df_meds["episodes"], alpha=0.7, label="Meds")
    plt.bar(df_nomeds["date"], df_nomeds["episodes"], alpha=0.7, label="No Meds")
    plt.xticks(rotation=45)
    plt.ylabel("Episodes per Day")
    plt.title("Episode Count per Day")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "episodes_per_day.png"))

def plot_hourly_avg_line(hourly_meds, hourly_nomeds):
    # Average minutes per hour across days
    meds_avg = hourly_meds.groupby("hour")["active_seconds"].mean() / 60.0
    nomeds_avg = hourly_nomeds.groupby("hour")["active_seconds"].mean() / 60.0

    # Align hour indices (0..H-1) based on union
    hours = sorted(set(meds_avg.index).union(set(nomeds_avg.index)))

    plt.figure(figsize=(12, 6))
    plt.plot(hours, [meds_avg.get(h, 0) for h in hours], marker="o", label="Meds")
    plt.plot(hours, [nomeds_avg.get(h, 0) for h in hours], marker="o", label="No Meds")
    plt.xlabel("Hour from video start")
    plt.ylabel("Average Minutes in Wheel")
    plt.title("Hourly Activity (Average Minutes per Hour)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(ADV_DIR, "hourly_avg_minutes.png"))

def plot_hourly_heatmap(hourly_long: pd.DataFrame, title: str, out_path: str):
    """
    Create a heatmap: rows = dates, cols = hours, values = active minutes.
    """
    if hourly_long.empty:
        return
    pivot = hourly_long.copy()
    pivot["active_min"] = pivot["active_seconds"] / 60.0
    table = pivot.pivot(index="date", columns="hour", values="active_min").fillna(0)
    # Simple imshow without specifying colors
    plt.figure(figsize=(max(10, table.shape[1] * 0.6), max(6, table.shape[0] * 0.3)))
    plt.imshow(table.values, aspect="auto", interpolation="nearest")
    plt.colorbar(label="Active minutes")
    plt.yticks(range(len(table.index)), table.index)
    plt.xticks(range(len(table.columns)), table.columns)
    plt.xlabel("Hour from video start")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path)

def plot_cumulative_curves(avg_meds: pd.DataFrame, avg_nomeds: pd.DataFrame):
    plt.figure(figsize=(12, 6))
    if not avg_meds.empty:
        plt.plot(avg_meds["t_sec"] / 3600.0, avg_meds["avg_cum_sec"] / 60.0, label="Meds")
    if not avg_nomeds.empty:
        plt.plot(avg_nomeds["t_sec"] / 3600.0, avg_nomeds["avg_cum_sec"] / 60.0, label="No Meds")
    plt.xlabel("Hours from video start")
    plt.ylabel("Average Cumulative Wheel Time (min)")
    plt.title("Cumulative Activity Curve (Average Across Days)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(ADV_DIR, "cumulative_average_minutes.png"))

def plot_episode_duration_hist(sessions_meds: pd.DataFrame, sessions_nomeds: pd.DataFrame):
    plt.figure(figsize=(12, 6))
    if not sessions_meds.empty:
        plt.hist(sessions_meds["duration_seconds"], bins=30, alpha=0.6, label="Meds")
    if not sessions_nomeds.empty:
        plt.hist(sessions_nomeds["duration_seconds"], bins=30, alpha=0.6, label="No Meds")
    plt.xlabel("Episode Duration (s)")
    plt.ylabel("Count")
    plt.title("Episode Duration Distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(ADV_DIR, "episode_duration_hist.png"))

def plot_daily_boxplot(df_meds: pd.DataFrame, df_nomeds: pd.DataFrame):
    plt.figure(figsize=(10, 6))
    data = [
        df_meds["total_running_time_min"].dropna().values,
        df_nomeds["total_running_time_min"].dropna().values
    ]
    plt.boxplot(data, labels=["Meds", "No Meds"], showfliers=True)
    plt.ylabel("Daily Total Running (min)")
    plt.title("Daily Total Running Time Variability")
    plt.tight_layout()
    plt.savefig(os.path.join(ADV_DIR, "daily_totals_boxplot.png"))

# =========================
# REPORT
# =========================
def print_report(df_meds, df_nomeds):
    print("\n=== 🐹 HAMSTER ANALYSIS REPORT ===")
    print("Days with meds:", len(df_meds))
    print("Days without meds:", len(df_nomeds))

    meds_total = df_meds["total_running_time_min"].sum()
    nomeds_total = df_nomeds["total_running_time_min"].sum()
    diff_min = meds_total - nomeds_total
    pct = (diff_min / nomeds_total * 100.0) if nomeds_total > 0 else float("nan")

    print("\n--- Total Running Time ---")
    print(f"With meds:    {meds_total:.2f} min ({meds_total/60:.2f} h)")
    print(f"Without meds: {nomeds_total:.2f} min ({nomeds_total/60:.2f} h)")
    sign = "+" if diff_min >= 0 else "-"
    print(f"Difference:   {sign}{abs(diff_min):.2f} min ({sign}{abs(pct):.2f}%)")

    print("\n--- Averages ---")
    print(f"Per-day running (meds):    {df_meds['total_running_time_min'].mean():.2f} min/day")
    print(f"Per-day running (no meds): {df_nomeds['total_running_time_min'].mean():.2f} min/day")
    print(f"Avg episode (meds):        {df_meds['avg_episode_duration_s'].mean():.2f} s")
    print(f"Avg episode (no meds):     {df_nomeds['avg_episode_duration_s'].mean():.2f} s")
    print(f"Episodes/day (meds):       {df_meds['episodes'].mean():.2f}")
    print(f"Episodes/day (no meds):    {df_nomeds['episodes'].mean():.2f}")

    print("\n✅ Charts saved in:")
    print(f"   - {PLOTS_DIR}")
    print(f"   - {ADV_DIR}")

# =========================
# MAIN
# =========================
def main():
    ensure_dirs()

    meds_path = os.path.join(DATA_DIR, "Meds")
    nomeds_path = os.path.join(DATA_DIR, "NoMeds")

    print("🔍 Processing Meds...")
    df_meds, sess_meds, hourly_meds, max_meds = process_folder(meds_path)

    print("🔍 Processing NoMeds...")
    df_nomeds, sess_nomeds, hourly_nomeds, max_nomeds = process_folder(nomeds_path)

    if df_meds.empty or df_nomeds.empty:
        print("❌ No valid data found. Check folders and CSVs.")
        input("\nPress Enter to exit...")
        return

    # Save data
    df_meds.to_csv("summary_meds.csv", index=False)
    df_nomeds.to_csv("summary_nomeds.csv", index=False)
    sess_meds.to_csv("sessions_meds.csv", index=False)
    sess_nomeds.to_csv("sessions_nomeds.csv", index=False)
    hourly_meds.to_csv("hourly_meds.csv", index=False)
    hourly_nomeds.to_csv("hourly_nomeds.csv", index=False)

    # Core plots
    plot_daily_totals(df_meds, df_nomeds)
    plot_avg_episode_duration(df_meds, df_nomeds)
    plot_episodes_per_day(df_meds, df_nomeds)

    # Advanced plots
    plot_hourly_avg_line(hourly_meds, hourly_nomeds)

    # Heatmaps
    plot_hourly_heatmap(hourly_meds, "Hourly Activity Heatmap (Meds)", os.path.join(ADV_DIR, "hourly_heatmap_meds.png"))
    plot_hourly_heatmap(hourly_nomeds, "Hourly Activity Heatmap (No Meds)", os.path.join(ADV_DIR, "hourly_heatmap_nomeds.png"))

    # Cumulative average curves (Option A: stop at longest across BOTH conditions)
    max_seconds = max(max_meds, max_nomeds)
    avg_meds = avg_cumulative_curve(sess_meds, max_seconds=max_seconds, step=60)
    avg_nomeds = avg_cumulative_curve(sess_nomeds, max_seconds=max_seconds, step=60)
    plot_cumulative_curves(avg_meds, avg_nomeds)

    # Episode duration histogram
    plot_episode_duration_hist(sess_meds, sess_nomeds)

    # Daily totals variability boxplot
    plot_daily_boxplot(df_meds, df_nomeds)

    # Report
    print_report(df_meds, df_nomeds)

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
