"""
Step 2: load every raw file into DuckDB as the bronze table.

Bronze = the source data with consistent column names and nothing else changed.
Every row keeps the file it came from, so any number can be traced to its source.
"""
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

RAW = Path("data/raw")
DB = Path("data/waitlist.duckdb")

# The 2026 files renamed some columns. Map both versions to one name.
RENAME = {
    "date": "snapshot_date", "Date": "snapshot_date",
    "clinicID": "clinic_id", "ClinicID": "clinic_id",
    "clinicName": "clinic_name", "ClinicName": "clinic_name",
    "HHS_ID": "hhs_code",
    "Hospital and Health Service": "hhs_name",
    "Area": "list_name",
}
for prefix in ("Waiting", "Treated"):
    for i in range(1, 8):
        RENAME[f"{prefix} D{i}"] = f"{prefix.lower()}_d{i}"

COLUMNS = [
    "snapshot_date", "clinic_id", "clinic_name", "hhs_code", "hhs_name", "list_name",
    *[f"waiting_d{i}" for i in range(1, 8)],
    *[f"treated_d{i}" for i in range(1, 8)],
]


def read_file(path):
    sheets = pd.ExcelFile(path).sheet_names
    data_sheet = "Data" if "Data" in sheets else next(s for s in sheets if s != "Notes")

    df = pd.read_excel(path, sheet_name=data_sheet, dtype=str)
    df = df.rename(columns=RENAME)

    unknown = set(df.columns) - set(COLUMNS)
    if unknown:
        raise ValueError(f"{path.name}: unexpected columns {unknown}")

    df = df.reindex(columns=COLUMNS)        # older files get an empty hhs_code
    df = df.dropna(subset=["list_name"])    # skip blank rows at the end of a sheet
    df["source_file"] = path.name
    df["source_sheet"] = data_sheet
    return df


def main():
    files = sorted(RAW.glob("*.xlsx"))
    frames = []
    for path in files:
        df = read_file(path)
        frames.append(df)
        print(f"  {path.name:45s} {len(df):4d} rows")

    bronze = pd.concat(frames, ignore_index=True)
    bronze["loaded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    con = duckdb.connect(str(DB))
    con.register("bronze_df", bronze)
    con.execute("CREATE OR REPLACE TABLE bronze_waitlist AS SELECT * FROM bronze_df")
    loaded = con.execute("SELECT COUNT(*) FROM bronze_waitlist").fetchone()[0]
    con.close()

    print(f"\nFiles read: {len(files)}")
    print(f"Rows read: {len(bronze):,} | rows in bronze_waitlist: {loaded:,}")
    if loaded != len(bronze):
        raise RuntimeError("Row count mismatch between files and DuckDB")


if __name__ == "__main__":
    main()