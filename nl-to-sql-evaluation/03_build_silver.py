"""
Step 3: build the silver table from bronze.

Silver = typed, standardised and flagged data. Every cleaning rule lives in
sql/silver_waitlist.sql or in the reference files in ref/, so it can be reviewed.
"""
from pathlib import Path

import duckdb

DB = "data/waitlist.duckdb"


def main():
    con = duckdb.connect(DB)
    con.execute("""
        CREATE OR REPLACE TABLE ref_hhs_alias AS
        SELECT * FROM read_csv('ref/hhs_alias.csv', header = true, all_varchar = true)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE ref_lists AS
        SELECT * FROM read_csv('ref/lists.csv', header = true)
    """)
    con.execute(Path("sql/silver_waitlist.sql").read_text())

    bronze_rows = con.execute("SELECT COUNT(*) FROM bronze_waitlist").fetchone()[0]
    rows, no_hhs, no_list, bad_pct, inquiry, hhs_level = con.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE hhs_code IS NULL),
               COUNT(*) FILTER (WHERE list_group IS NULL),
               COUNT(*) FILTER (WHERE flag_invalid_pct),
               COUNT(*) FILTER (WHERE flag_includes_inquiry),
               COUNT(*) FILTER (WHERE report_level = 'HHS')
        FROM silver_waitlist
    """).fetchone()
    con.close()

    print(f"Rows: bronze {bronze_rows:,} | silver {rows:,}")
    print(f"Rows without a standard HHS: {no_hhs}")
    print(f"Rows without a known list: {no_list}")
    print(f"Rows flagged: invalid % {bad_pct} | includes Inquiry {inquiry} | HHS-level GA {hhs_level}")


if __name__ == "__main__":
    main()