"""
Queensland influenza: when will the 2027 season peak?

Data: NNDSS public dataset - Influenza (laboratory confirmed), 2008-2024
      https://www.cdc.gov.au/resources/publications/nndss-dataset-influenza
      (one row per notification: week ending, state, age group, sex, ...)

Method
  1. Aggregate Queensland notifications to ISO weeks.
  2. Turn each season into a "shape": share of that season's cases per week
     (3-week rolling average). This forecasts TIMING, not volume.
  3. Backtest: predict each season's peak week using only earlier seasons.
  4. Forecast 2027 as a recency-weighted ensemble of 12 seasons
     (2011-2019 and 2022-2024; post-COVID seasons weighted 3x).
     Excluded: 2009 (pandemic), 2010 (post-pandemic), 2020-21 (COVID).
  5. 80% interval for the peak week by bootstrapping seasons.

Run:  python qld_flu_peak_forecast.py path/to/nndss-public-dataset-influenza.xlsx
"""
import sys
import datetime as dt
from collections import Counter

import numpy as np
import openpyxl

PRE_COVID = list(range(2011, 2020))
POST_COVID = [2022, 2023, 2024]
SEASONS = PRE_COVID + POST_COVID


def load_qld_weekly(path):
    """Count Queensland notifications per week-ending date across all sheets."""
    wb = openpyxl.load_workbook(path, read_only=True)
    weekly = Counter()
    for ws in wb.worksheets:
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i < 2:  # title row + header row
                continue
            week_ending, state = row[0], row[1]
            if isinstance(week_ending, dt.datetime) and state == "Qld":
                weekly[week_ending.date()] += 1
    return weekly


def season_shape(weekly, year):
    """Share of the season's cases in each ISO week (52 weeks), smoothed."""
    counts = np.zeros(53)
    for day, n in weekly.items():
        if day.year == year:
            counts[min(day.isocalendar()[1], 53) - 1] += n
    counts = counts[:52]
    share = counts / counts.sum()
    return np.convolve(share, np.ones(3) / 3, mode="same")


def peak_week(shape):
    return int(np.argmax(shape)) + 1


def main(path):
    weekly = load_qld_weekly(path)
    total = sum(weekly.values())
    print(f"Queensland notifications loaded: {total:,}")

    shapes = {y: season_shape(weekly, y) for y in SEASONS}
    actual = {y: peak_week(shapes[y]) for y in SEASONS}
    print("Actual peak week by season:", actual)

    # Backtest: expanding window, train only on earlier seasons
    print("\nBacktest (predicted vs actual peak week)")
    errors = []
    for y in SEASONS:
        train = [s for s in SEASONS if s < y]
        if len(train) < 2:
            continue
        pred = peak_week(np.mean([shapes[s] for s in train], axis=0))
        err = abs(pred - actual[y])
        errors.append((y, err))
        print(f"  {y}: predicted wk {pred}, actual wk {actual[y]}, error {err} wks")
    pre = [e for y, e in errors if y < 2020]
    print(f"Mean error 2013-2019: {np.mean(pre):.1f} wks")

    # 2027 forecast: recency-weighted ensemble + bootstrap interval
    weights = np.array([3.0 if s in POST_COVID else 1.0 for s in SEASONS])
    weights /= weights.sum()
    stack = np.array([shapes[s] for s in SEASONS])
    forecast = np.average(stack, axis=0, weights=weights)

    rng = np.random.default_rng(1)
    boot = []
    for _ in range(5000):
        pick = rng.choice(len(SEASONS), size=len(SEASONS), p=weights)
        boot.append(peak_week(stack[pick].mean(axis=0)))
    p10, p50, p90 = np.percentile(boot, [10, 50, 90]).astype(int)

    def week_dates(w):
        start = dt.date.fromisocalendar(2027, w, 1)
        return f"{start:%d %b} - {start + dt.timedelta(6):%d %b %Y}"

    print("\n2027 forecast")
    print(f"  Most likely peak: week {p50} ({week_dates(p50)})")
    print(f"  80% interval: weeks {p10}-{p90} ({week_dates(p10)[:6]} to {week_dates(p90)[-11:]})")

    # Share of each season's cases before 31 March (before vaccine availability)
    before_april = []
    for y in SEASONS:
        days = [d for d in weekly if d.year == y]
        season_total = sum(weekly[d] for d in days)
        early = sum(weekly[d] for d in days if d <= dt.date(y, 3, 31))
        before_april.append(100 * early / season_total)
    print(f"  Median share of cases before 31 March: {np.median(before_april):.1f}%")

    return forecast


if __name__ == "__main__":
    main(sys.argv[1])
