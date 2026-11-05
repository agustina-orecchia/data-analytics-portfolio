"""
Synthetic patient-level GA waiting list for the prototype.

No real patient data is used. The list is calibrated so that its totals match
the published Metro South GA list at 31 December 2025: 964 people, the same
category mix and the same months-waited distribution.

Run:
  python make_synthetic_list.py      (writes ga_list_synthetic.csv and
                                      injects the data into waitlist_prototype.html)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(31)
AS_AT = pd.Timestamp("2025-12-31")
HERE = Path(__file__).parent

# Published Metro South GA list, Dec 2025: count per months-waited bin
BINS = {
    1: [(0, 1, 1)],
    2: [(0, 3, 77), (3, 6, 86), (6, 9, 99), (9, 12, 80), (12, 15, 64), (15, 30, 397)],
    3: [(0, 6, 41), (6, 12, 34), (12, 18, 32), (18, 24, 21), (24, 30, 11), (30, 42, 21)],
}
TARGET_DAYS = {1: 30, 2: 90, 3: 365}
CLINICS = ["Clinic A", "Clinic B", "Clinic C", "Clinic D", "Clinic E"]
CLINIC_WEIGHTS = [0.30, 0.22, 0.20, 0.16, 0.12]


def build():
    rows = []
    for cat, bins in BINS.items():
        for lo, hi, n in bins:
            for _ in range(n):
                days = int(RNG.uniform(lo * 30.4, hi * 30.4))
                rows.append({"category": cat, "days_waiting": days})
    d = pd.DataFrame(rows)
    d["patient_id"] = [f"SYN{100000 + i}" for i in RNG.permutation(len(d))]
    d["clinic"] = RNG.choice(CLINICS, size=len(d), p=CLINIC_WEIGHTS)
    d["cohort"] = np.where(RNG.random(len(d)) < 0.78, "Child (0-14)", "Adult, additional needs")
    d["listed_date"] = AS_AT - pd.to_timedelta(d.days_waiting, unit="D")
    # Last contact: most long waiters have not been contacted for months
    gap = np.minimum(d.days_waiting, RNG.exponential(150, len(d)).astype(int))
    d["last_contact_date"] = AS_AT - pd.to_timedelta(gap, unit="D")
    d["pre_anaesthetic_done"] = RNG.random(len(d)) < np.clip(d.days_waiting / 900, 0.15, 0.7)
    d["target_days"] = d.category.map(TARGET_DAYS)
    d["days_to_target"] = d.target_days - d.days_waiting
    d["status"] = np.select(
        [d.days_to_target < 0, d.days_to_target <= 30],
        ["Past target", "Due in 30 days"], "Within target")
    d["validation_due"] = (AS_AT - d.last_contact_date).dt.days > 90
    # Treat-in-turn rank: clinical category first, then longest wait relative to target
    d["urgency"] = d.days_waiting / d.target_days
    d = d.sort_values(["category", "urgency"], ascending=[True, False])
    d["book_rank"] = range(1, len(d) + 1)
    return d.sort_values("patient_id").reset_index(drop=True)


def main():
    d = build()
    assert len(d) == 964
    d.to_csv(HERE / "ga_list_synthetic.csv", index=False, date_format="%Y-%m-%d")
    print(d.groupby("category").size().to_string())
    print(d.status.value_counts().to_string())
    print(f"Validation due: {d.validation_due.sum()}")

    keep = ["patient_id", "category", "days_waiting", "clinic", "cohort", "listed_date",
            "last_contact_date", "pre_anaesthetic_done", "days_to_target", "status",
            "validation_due", "book_rank"]
    data = d[keep].copy()
    for c in ["listed_date", "last_contact_date"]:
        data[c] = data[c].dt.strftime("%Y-%m-%d")
    payload = json.dumps(data.to_dict(orient="records"), separators=(",", ":"))
    html = (HERE / "waitlist_prototype.html").read_text()
    start, end = "/*DATA_START*/", "/*DATA_END*/"
    i, j = html.index(start) + len(start), html.index(end)
    (HERE / "waitlist_prototype.html").write_text(html[:i] + payload + html[j:])
    print("Data injected into waitlist_prototype.html")


if __name__ == "__main__":
    main()
