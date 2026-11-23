"""
Step 5: data quality tests on bronze, silver and gold.

Each test is a SQL query that returns the number of rows breaking a rule.
- error: the pipeline stops (exit code 1). The data cannot be trusted.
- warn: the result is reported but the pipeline continues. Known issue to keep an eye on.
"""
import sys

import duckdb

DB = "data/waitlist.duckdb"

TESTS = [
    # Bronze to silver
    {
        "name": "No rows lost between bronze and silver",
        "severity": "error",
        "sql": """SELECT ABS((SELECT COUNT(*) FROM bronze_waitlist)
                           - (SELECT COUNT(*) FROM silver_waitlist))""",
    },
    {
        "name": "One row per snapshot, clinic and list (grain)",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM (
                      SELECT snapshot_date, clinic_id, list_name
                      FROM silver_waitlist
                      GROUP BY ALL HAVING COUNT(*) > 1)""",
    },
    {
        "name": "Every HHS maps to a standard name",
        "severity": "error",
        "sql": "SELECT COUNT(*) FROM silver_waitlist WHERE hhs_code IS NULL",
    },
    {
        "name": "Every list is a known list",
        "severity": "error",
        "sql": "SELECT COUNT(*) FROM silver_waitlist WHERE list_group IS NULL",
    },
    {
        "name": "HHS code in the file agrees with the mapped code",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM silver_waitlist
                  WHERE hhs_code_source IS NOT NULL AND hhs_code_source <> hhs_code""",
    },
    {
        "name": "Counts are not negative",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM silver_waitlist
                  WHERE LEAST(waiting_d1, waiting_d2, waiting_d3, waiting_d4, waiting_d5, waiting_d6,
                              treated_d1, treated_d2, treated_d3, treated_d4, treated_d5, treated_d6) < 0""",
    },
    {
        "name": "Each file has a single snapshot date",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM (
                      SELECT source_file FROM silver_waitlist
                      GROUP BY source_file HAVING COUNT(DISTINCT snapshot_date) > 1)""",
    },
    {
        "name": "Snapshot dates are the last day of a month",
        "severity": "error",
        "sql": "SELECT COUNT(*) FROM silver_waitlist WHERE snapshot_date <> last_day(snapshot_date)",
    },
    {
        "name": "No gaps between snapshots",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM (
                      SELECT snapshot_date, period_months,
                             date_diff('month', LAG(snapshot_date) OVER (ORDER BY snapshot_date),
                                       snapshot_date) AS gap
                      FROM (SELECT DISTINCT snapshot_date, period_months FROM silver_waitlist))
                  WHERE gap IS NOT NULL AND gap <> period_months""",
    },
    {
        "name": "Published % within target is between 0 and 100",
        "severity": "warn",
        "sql": "SELECT COUNT(*) FROM silver_waitlist WHERE flag_invalid_pct",
    },
    {
        "name": "Within-target rule reproduces the published % (rows off by more than 1 point)",
        "severity": "warn",
        "sql": """SELECT COUNT(*) FROM (
                      SELECT waiting_pct_within_published AS published,
                             100.0 * (waiting_d1 + CASE WHEN within_target_bins = 2 THEN waiting_d2 ELSE 0 END)
                             / NULLIF(waiting_d1 + waiting_d2 + waiting_d3 + waiting_d4
                                      + waiting_d5 + waiting_d6, 0) AS recalculated
                      FROM silver_waitlist)
                  WHERE published IS NOT NULL AND recalculated IS NOT NULL
                    AND ABS(published - recalculated) > 1""",
    },
    {
        "name": "Latest snapshot is less than 9 months old (freshness)",
        "severity": "warn",
        "sql": """SELECT CASE WHEN date_diff('month', MAX(snapshot_date), current_date) > 9
                         THEN 1 ELSE 0 END FROM silver_waitlist""",
    },
    # Gold
    {
        "name": "Gold fact has one row per silver row",
        "severity": "error",
        "sql": """SELECT ABS((SELECT COUNT(*) FROM silver_waitlist)
                           - (SELECT COUNT(*) FROM fact_waitlist))""",
    },
    {
        "name": "Within target + past target = total waiting",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM fact_waitlist
                  WHERE waiting_within_target + waiting_past_target <> waiting_total""",
    },
    {
        "name": "Wait bands add up to the fact table",
        "severity": "error",
        "sql": """SELECT COUNT(*) FROM (
                      SELECT f.snapshot_date, f.clinic_id, f.list_name, f.waiting_total
                      FROM fact_waitlist AS f
                      JOIN fact_wait_band AS b USING (snapshot_date, clinic_id, list_name)
                      GROUP BY ALL HAVING f.waiting_total <> SUM(b.waiting))""",
    },
]


def main():
    con = duckdb.connect(DB, read_only=True)
    errors = 0
    for test in TESTS:
        failing = con.execute(test["sql"]).fetchone()[0]
        if failing == 0:
            status = "PASS"
        elif test["severity"] == "error":
            status = "FAIL"
            errors += 1
        else:
            status = "WARN"
        print(f"[{status}] {test['name']}: {failing}")
    con.close()

    print(f"\n{len(TESTS)} tests, {errors} failed")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()