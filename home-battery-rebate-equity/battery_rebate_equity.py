"""
Cheaper Home Batteries: are renters being left behind?

Joins three public datasets by postcode and tests whether postcodes with more
renters install fewer subsidised home batteries, after controlling for
socio-economic status.

Inputs (download from the sources listed in README.md):
  1. CER  - sgu-battery-installations-2011-to-present-and-totals.csv
  2. ABS  - 2021_GCP_POA_for_AUS_short-header.zip  (Census table G37)
  3. ABS  - Postal_Area_Indexes_SEIFA_2021.xlsx

Run:
  python battery_rebate_equity.py battery.csv census.zip seifa.xlsx

Output:
  data/qld_postcode_dataset.csv and a printed summary of all checks and results.
"""
import csv
import io
import sys
import zipfile

import numpy as np
import openpyxl

G37_PATH = "2021 Census GCP Postal Areas for AUS/2021Census_G37_AUST_POA.csv"
MIN_HOUSES = 500  # drop small postcodes where rates are unstable


def state_from_postcode(pc):
    p = int(pc)
    if 4000 <= p <= 4999 or 9000 <= p <= 9999:
        return "QLD"
    if 1000 <= p <= 2599 or 2620 <= p <= 2899 or 2921 <= p <= 2999:
        return "NSW"
    if 200 <= p <= 299 or 2600 <= p <= 2619 or 2900 <= p <= 2920:
        return "ACT"
    if 3000 <= p <= 3999 or 8000 <= p <= 8999:
        return "VIC"
    if 5000 <= p <= 5999:
        return "SA"
    if 6000 <= p <= 6999:
        return "WA"
    if 7000 <= p <= 7999:
        return "TAS"
    if 800 <= p <= 999:
        return "NT"
    return "OTHER"


def load_batteries(path):
    """Installations per postcode; checks monthly columns add up to the total."""
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    months = [h.split(" - ")[0] for h in rows[0][1:-1]]
    per_postcode, per_month = {}, np.zeros(len(months), dtype=int)
    for r in rows[1:]:
        vals = [int(float(x or 0)) for x in r[1:-1]]
        assert sum(vals) == int(float(r[-1] or 0)), f"Monthly sum mismatch in {r[0]}"
        per_postcode[r[0].strip().zfill(4)] = sum(vals)
        per_month += vals
    return per_postcode, dict(zip(months, per_month.tolist()))


def load_census(zip_path):
    """Dwellings by tenure and structure (Census 2021, table G37)."""
    out = {}
    with zipfile.ZipFile(zip_path) as z:
        text = io.TextIOWrapper(z.open(G37_PATH), encoding="utf-8")
        for r in csv.DictReader(text):
            pc = r["POA_CODE_2021"].replace("POA", "")
            out[pc] = {
                "houses": int(r["Total_DS_Sep_house"]),
                "rented_houses": int(r["R_Tot_DS_Sep_house"]),
                "dwellings": int(r["Total_Total"]),
            }
    return out


def load_seifa(path):
    """IRSAD score and decile by postal area (SEIFA 2021, Table 1)."""
    ws = openpyxl.load_workbook(path, read_only=True)["Table 1"]
    out = {}
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i < 6 or not r[0] or not isinstance(r[3], (int, float)):
            continue
        out[str(r[0]).zfill(4)] = {"irsad": r[3], "decile": r[4], "caution": bool(r[10])}
    return out


def pooled_rate(rows):
    return 1000 * sum(r["batteries"] for r in rows) / sum(r["houses"] for r in rows)


def main(battery_csv, census_zip, seifa_xlsx):
    batteries, monthly = load_batteries(battery_csv)
    census, seifa = load_census(census_zip), load_seifa(seifa_xlsx)
    total = sum(batteries.values())
    print(f"Installations Jul 2025 onward: {total:,}")
    print("By month:", monthly)

    joined = []
    for pc, c in census.items():
        if pc in seifa and c["dwellings"] > 0:
            joined.append({"postcode": pc, "state": state_from_postcode(pc),
                           "batteries": batteries.get(pc, 0), **c, **seifa[pc]})
    matched = sum(r["batteries"] for r in joined)
    print(f"Matched to Census postal areas: {matched:,} ({100 * matched / total:.2f}%)")

    # Validation: reproduce the Australian Energy Council's national split
    hi = sum(r["batteries"] for r in joined if r["decile"] >= 8)
    lo = sum(r["batteries"] for r in joined if r["decile"] <= 3)
    print(f"Share in SEIFA deciles 8-10: {100 * hi / matched:.1f}% (AEC: 41.0%)")
    print(f"Share in SEIFA deciles 1-3:  {100 * lo / matched:.1f}% (AEC: 17.8%)")

    qld = [r for r in joined if r["state"] == "QLD"
           and r["houses"] >= MIN_HOUSES and not r["caution"]]
    for r in qld:
        r["per_1000_houses"] = 1000 * r["batteries"] / r["houses"]
        r["renter_share"] = r["rented_houses"] / r["houses"]
    print(f"\nQueensland postcodes analysed: {len(qld)}")

    # Renter-share thirds
    shares = np.array([r["renter_share"] for r in qld])
    t1, t2 = np.percentile(shares, [100 / 3, 200 / 3])
    low = [r for r in qld if r["renter_share"] <= t1]
    high = [r for r in qld if r["renter_share"] > t2]
    print(f"Batteries per 1,000 houses: low-renter third {pooled_rate(low):.1f}, "
          f"high-renter third {pooled_rate(high):.1f} "
          f"({100 * (pooled_rate(high) / pooled_rate(low) - 1):.0f}%)")

    # Within each SEIFA decile: below vs above the decile's median renter share
    print("\nWithin SEIFA decile (low-renter half vs high-renter half):")
    for dec in range(1, 11):
        rows = [r for r in qld if r["decile"] == dec]
        med = np.median([r["renter_share"] for r in rows])
        a = pooled_rate([r for r in rows if r["renter_share"] <= med])
        b = pooled_rate([r for r in rows if r["renter_share"] > med])
        print(f"  Decile {dec:>2}: {a:6.1f} vs {b:6.1f} ({100 * (b / a - 1):+.0f}%)")

    # Weighted regression: log(rate) ~ renter share + standardised IRSAD
    def renter_effect(rows):
        rate = np.array([r["per_1000_houses"] for r in rows])
        rent = np.array([r["renter_share"] for r in rows])
        irsad = np.array([r["irsad"] for r in rows])
        X = np.column_stack([np.ones(len(rows)), rent, (irsad - irsad.mean()) / irsad.std()])
        w = np.sqrt([r["houses"] for r in rows])
        beta, *_ = np.linalg.lstsq(X * w[:, None], np.log(rate + 1) * w, rcond=None)
        return 100 * (np.exp(beta[1] * 0.10) - 1)

    print(f"\nEffect of +10 points renter share (controlling for SEIFA): "
          f"{renter_effect(qld):.1f}%")
    print(f"Robustness, excluding postcodes above 50% renters: "
          f"{renter_effect([r for r in qld if r['renter_share'] <= 0.5]):.1f}%")

    with open("data/qld_postcode_dataset.csv", "w", newline="") as f:
        cols = ["postcode", "batteries", "houses", "rented_houses", "renter_share",
                "per_1000_houses", "irsad", "decile"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(qld, key=lambda r: r["postcode"]):
            w.writerow({**r, "renter_share": round(r["renter_share"], 4),
                        "per_1000_houses": round(r["per_1000_houses"], 2),
                        "irsad": round(r["irsad"], 1)})
    print("\nSaved data/qld_postcode_dataset.csv")


if __name__ == "__main__":
    main(*sys.argv[1:4])
