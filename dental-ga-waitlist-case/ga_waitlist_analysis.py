"""
Public dental general anaesthetic (GA) waiting lists, Queensland
Capacity, demand and on-time performance by Hospital and Health Service (HHS)

Supports the business case in README.md. Every figure quoted there is printed
by this script.

Input:
  data/raw_ga_extract.csv  GA rows from the 34 Queensland Health public dental
                           waiting list files, Jul 2021 to Dec 2025, summed to
                           HHS x GA category x snapshot date.
                           w1..w6 = clients waiting by months-waited bin
                           t1..t6 = clients treated in the period, same bins

Run:
  python ga_waitlist_analysis.py

Outputs:
  data/ga_hhs_snapshot.csv, data/ga_hhs_benchmark_2025.csv, images/*.png
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Bins past the clinically recommended time, per GA category.
# Bin edges (months): Cat 1 <1, 1-2, ...; Cat 2 <3, 4-6, ...; Cat 3 <6, 7-12, 13-18, ...
OVERDUE_FROM_BIN = {1: 2, 2: 2, 3: 3}          # first overdue bin (1-based)
TARGET_MONTHS = {1: 1, 2: 3, 3: 12}

NEP_2025_26 = 7258        # $ per NWAU(25), IHACPA NEP Determination 2025-26
D40Z_INLIER_PW = 0.7976   # AR-DRG V11.0 D40Z Dental Extractions and Restorations
COST_PER_EPISODE = NEP_2025_26 * D40Z_INLIER_PW

# Option B: list validation and triage audit (assumptions, to confirm with the HHS)
AO4_TOP = 103572          # $ per year, HHS General Employees Award AO4 pay point 4, from 1 Sep 2025
ON_COSTS = 0.25           # assumed superannuation, leave and payroll tax loading
VALIDATION_FTE_MONTHS = 6
VALIDATION_COST = AO4_TOP * (1 + ON_COSTS) * VALIDATION_FTE_MONTHS / 12

FOCUS, BENCHMARK = "Metro South", "Wide Bay"
INK, MUTED, GRID, OTHER = "#252423", "#605E5C", "#E1DFDD", "#C8C6C4"
COLOURS = {FOCUS: "#E044A7", BENCHMARK: "#6B007B"}


def load():
    d = pd.read_csv("data/raw_ga_extract.csv")
    d["date"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(d.date_serial, unit="D")
    w = [f"w{i}" for i in range(1, 7)]
    t = [f"t{i}" for i in range(1, 7)]
    d["waiting"] = d[w].sum(axis=1)
    d["treated"] = d[t].sum(axis=1)
    d["overdue"] = [r[w[OVERDUE_FROM_BIN[r.ga_category] - 1:]].sum() for _, r in d.iterrows()]
    # Category-neutral measure: waited more than 12 months, whatever the category
    over12 = {1: [], 2: ["w5", "w6"], 3: ["w3", "w4", "w5", "w6"]}
    d["over_12m"] = [r[over12[r.ga_category]].sum() if over12[r.ga_category] else 0 for _, r in d.iterrows()]
    d["treated_late"] = [r[t[OVERDUE_FROM_BIN[r.ga_category] - 1:]].sum() for _, r in d.iterrows()]
    # Monthly files until June 2023, quarterly files after
    d["months_in_period"] = np.where(d.date <= "2023-06-30", 1, 3)
    return d


def hhs_snapshot(d):
    s = (d.groupby(["date", "hhs"])
          [["waiting", "overdue", "over_12m", "treated", "treated_late", "months_in_period"]]
          .agg({"waiting": "sum", "overdue": "sum", "over_12m": "sum", "treated": "sum",
                "treated_late": "sum", "months_in_period": "max"})
          .reset_index())
    s["pct_overdue"] = s.overdue / s.waiting.where(s.waiting > 0)
    s["treated_per_month"] = s.treated / s.months_in_period
    return s


def benchmark_2025(d, s):
    """Calendar 2025: four quarterly files."""
    y = s[(s.date >= "2025-03-31") & (s.date <= "2025-12-31")]
    b = y.groupby("hhs").agg(treated_2025=("treated", "sum"),
                             treated_late_2025=("treated_late", "sum"),
                             avg_waiting=("waiting", "mean"))
    last = s[s.date == s.date.max()].set_index("hhs")
    first = s[s.date == "2024-12-31"].set_index("hhs")
    b["waiting_dec25"] = last.waiting
    b["overdue_dec25"] = last.overdue
    b["pct_overdue_dec25"] = last.pct_overdue
    b["pct_over_12m_dec25"] = last.over_12m / last.waiting
    b["waiting_dec24"] = first.waiting
    b["treated_per_month"] = b.treated_2025 / 12
    b["pct_treated_on_time"] = 1 - b.treated_late_2025 / b.treated_2025
    # Net additions = change in list + treated (removals without treatment are not published)
    b["net_additions_per_month"] = (b.waiting_dec25 - b.waiting_dec24 + b.treated_2025) / 12
    b["months_to_clear_list"] = b.waiting_dec25 / b.treated_per_month
    b["throughput_vs_demand"] = b.treated_per_month / b.net_additions_per_month
    # Category mix of the list at Dec 2025
    mix = d[d.date == d.date.max()].pivot_table(index="hhs", columns="ga_category",
                                                values="waiting", aggfunc="sum").fillna(0)
    for c in (1, 2, 3):
        b[f"share_cat{c}"] = mix[c] / mix.sum(axis=1)
    return b.sort_values("waiting_dec25", ascending=False)


def backlog_scenarios(b, hhs, months=(12, 18, 24), removed_by_validation=(0, 0.10, 0.20)):
    """Extra GA cases needed to clear the overdue backlog in m months.

    Inflow is held at the 2025 level; the 2025 surplus of throughput over
    inflow already works the backlog down, so only the gap is costed.
    `removed_by_validation` is the share of overdue patients assumed to leave the
    list after validation (moved, treated elsewhere, no longer need GA).
    """
    r = b.loc[hhs]
    surplus = max(0.0, r.treated_per_month - r.net_additions_per_month)
    rows = []
    for v in removed_by_validation:
        backlog = r.overdue_dec25 * (1 - v)
        for m in months:
            extra = max(0.0, backlog / m - surplus)
            rows.append({"removed_by_validation": v, "clear_in_months": m,
                         "extra_cases_per_month": extra,
                         "uplift_vs_2025_throughput": extra / r.treated_per_month,
                         "total_extra_cases": extra * m,
                         "total_extra_cost": extra * m * COST_PER_EPISODE})
    return pd.DataFrame(rows), surplus


def style(ax):
    ax.set_axisbelow(True)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]:
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=MUTED)


def chart_trend(s, path):
    qld = s.groupby("date")[["waiting", "overdue"]].sum()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5), dpi=150)
    for h in s.hhs.unique():
        g = s[(s.hhs == h) & (s.waiting >= 20)]
        if h in COLOURS:
            continue
        a1.plot(g.date, g.pct_overdue * 100, color=OTHER, linewidth=1, zorder=1)
    a1.plot(qld.index, qld.overdue / qld.waiting * 100, color=INK, linewidth=1.6,
            linestyle="--", label="Queensland", zorder=2)
    for h, c in COLOURS.items():
        g = s[s.hhs == h]
        a1.plot(g.date, g.pct_overdue * 100, color=c, linewidth=2.2, label=h, zorder=3)
        a1.annotate(f"{g.pct_overdue.iloc[-1]:.0%}", (g.date.iloc[-1], g.pct_overdue.iloc[-1] * 100),
                    xytext=(6, -3), textcoords="offset points", fontsize=9, color=INK)
    a1.set_ylim(0, 100)
    a1.set_title("Share of the GA list past its clinical target\n(grey lines: other HHSs)",
                 loc="left", fontsize=11, color=INK)
    a1.legend(frameon=False, fontsize=9, loc="upper left")
    a1.grid(axis="y", color=GRID)

    for h, c in COLOURS.items():
        g = s[s.hhs == h].copy()
        g["q"] = g.date.dt.to_period("Q")
        q = g.groupby("q").agg(waiting=("waiting", "last"), treated=("treated", "sum"))
        q["treated_12m"] = q.treated.rolling(4).sum()
        x = q.index.to_timestamp(how="end")
        a2.plot(x, q.waiting, color=c, linewidth=2.2, label=f"{h}: waiting")
        a2.plot(x, q.treated_12m, color=c, linewidth=1.6, linestyle=":",
                label=f"{h}: treated in the last 12 months")
    a2.set_title("List size vs patients treated in the previous 12 months\n(quarter end)", loc="left", fontsize=11, color=INK)
    a2.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    a2.set_ylim(0, 1450)
    a2.grid(axis="y", color=GRID)
    a2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    import matplotlib.dates as mdates
    for ax in (a1, a2):
        style(ax)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_benchmark(b, path):
    t = b[b.waiting_dec25 >= 50].sort_values("months_to_clear_list")
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150)
    cols = [COLOURS.get(h, OTHER) for h in t.index]
    ax.barh(t.index, t.months_to_clear_list, color=cols, height=0.62)
    for i, (h, r) in enumerate(t.iterrows()):
        ax.text(r.months_to_clear_list + 0.4, i,
                f"{r.months_to_clear_list:.0f} months  ·  {r.pct_over_12m_dec25:.0%} waited 12+ months",
                va="center", fontsize=8.5, color=INK)
    ax.set_xlabel("Months to treat everyone on the Dec 2025 list at the 2025 treatment rate", color=MUTED)
    ax.set_title("At its 2025 treatment rate, Metro South would need 32 months to treat its current list\n"
                 "HHSs with 50+ people on the GA list, Dec 2025", loc="left", fontsize=11.5, color=INK)
    ax.set_xlim(0, 62)
    ax.grid(axis="x", color=GRID)
    ax.tick_params(axis="y", length=0)
    style(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    d = load()
    print("== Validation")
    print(f"Snapshots: {d.date.nunique()} ({d.date.min():%b %Y} to {d.date.max():%b %Y}); HHSs: {d.hhs.nunique()}")
    assert d.ga_category.isin([1, 2, 3]).all()
    assert (d.overdue <= d.waiting).all()
    june = d[d.date.dt.month.eq(6) & d.date.dt.year.eq(2025)]
    print(f"June 2025 GA waiting, all HHSs: {june.waiting.sum():,} (matches fluoridation project total 3,525)")
    print(f"Cost per GA dental episode (NEP25 x D40Z inlier weight): ${COST_PER_EPISODE:,.0f}")

    s = hhs_snapshot(d)
    s.round(4).to_csv("data/ga_hhs_snapshot.csv", index=False, date_format="%Y-%m-%d")
    b = benchmark_2025(d, s)
    b.round(3).to_csv("data/ga_hhs_benchmark_2025.csv")

    qld = s[s.date == s.date.max()][["waiting", "overdue"]].sum()
    print(f"\nQueensland, Dec 2025: {qld.waiting:,} waiting, {qld.overdue:,} past target ({qld.overdue / qld.waiting:.0%})")
    print(f"{FOCUS} share of all overdue: {b.loc[FOCUS, 'overdue_dec25'] / qld.overdue:.0%}")

    print("\n== Benchmark, calendar 2025")
    cols = ["waiting_dec25", "overdue_dec25", "pct_overdue_dec25", "pct_over_12m_dec25", "treated_per_month",
            "net_additions_per_month", "throughput_vs_demand", "months_to_clear_list",
            "pct_treated_on_time", "share_cat1", "share_cat2", "share_cat3"]
    print(b[cols].round(2).to_string())

    print(f"\n== {FOCUS} vs {BENCHMARK}")
    for h in (FOCUS, BENCHMARK):
        g = s[s.hhs == h]
        print(f"{h}: list {g.waiting.iloc[0]:,} (Jul 2021) -> {g.waiting.iloc[-1]:,} (Dec 2025); "
              f"overdue {g.pct_overdue.iloc[0]:.0%} -> {g.pct_overdue.iloc[-1]:.0%}")

    ms = d[(d.hhs == FOCUS) & (d.date == d.date.max()) & (d.ga_category == 2)]
    print(f"{FOCUS} Category 2 (target 3 months) waiting more than 15 months: {int(ms.w6.sum())}")
    wb = s[s.hhs == BENCHMARK].set_index("date").waiting
    print(f"{BENCHMARK} list Dec 2023 -> Dec 2025: {wb['2023-12-31']} -> {wb['2025-12-31']} "
          f"({wb['2025-12-31'] / wb['2023-12-31'] - 1:+.0%})")

    print(f"\n== Clearing the {FOCUS} overdue backlog (inflow held at 2025 level)")
    sc, surplus = backlog_scenarios(b, FOCUS)
    print(f"Existing 2025 surplus of throughput over inflow: {surplus:.1f} cases/month")
    print(sc.round(2).to_string(index=False))
    print(f"\nValidation and triage audit cost (assumption): ${VALIDATION_COST:,.0f} "
          f"= {VALIDATION_COST / COST_PER_EPISODE:.1f} GA episodes")
    sc.round(2).to_csv("data/metro_south_backlog_scenarios.csv", index=False)

    chart_trend(s, "images/ga_overdue_trend.png")
    chart_benchmark(b, "images/ga_months_to_clear.png")
    print("\nCharts saved to images/")


if __name__ == "__main__":
    main()
