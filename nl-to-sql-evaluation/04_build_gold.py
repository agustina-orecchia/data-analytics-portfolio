"""
Step 4: build the gold tables from silver.

Gold = tables designed to answer business questions. This is the only layer the
language model will see, so names and measures must be unambiguous.
"""
from pathlib import Path

import duckdb

DB = "data/waitlist.duckdb"


def main():
    con = duckdb.connect(DB)
    con.execute("""
        CREATE OR REPLACE TABLE ref_lists AS
        SELECT * FROM read_csv('ref/lists.csv', header = true)
    """)
    con.execute(Path("sql/gold.sql").read_text())
    for table in ["dim_list", "dim_clinic", "fact_waitlist", "fact_wait_band"]:
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:16s} {rows:>7,} rows")
    con.close()


if __name__ == "__main__":
    main()