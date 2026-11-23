-- Silver: typed, standardised and flagged. One row per snapshot, clinic and list.
CREATE OR REPLACE TABLE silver_waitlist AS
WITH typed AS (
    SELECT
        CAST(LEFT(snapshot_date, 10) AS DATE)                    AS snapshot_date,
        CAST(clinic_id AS INTEGER)                                AS clinic_id,
        TRIM(clinic_name)                                         AS clinic_name_source,
        TRIM(hhs_name)                                            AS hhs_name_source,
        TRIM(hhs_code)                                            AS hhs_code_source,
        TRIM(list_name)                                           AS list_name,
        CAST(waiting_d1 AS INTEGER) AS waiting_d1,
        CAST(waiting_d2 AS INTEGER) AS waiting_d2,
        CAST(waiting_d3 AS INTEGER) AS waiting_d3,
        CAST(waiting_d4 AS INTEGER) AS waiting_d4,
        CAST(waiting_d5 AS INTEGER) AS waiting_d5,
        CAST(waiting_d6 AS INTEGER) AS waiting_d6,
        CAST(NULLIF(TRIM(waiting_d7), '-') AS DOUBLE)             AS waiting_pct_within_published,
        CAST(treated_d1 AS INTEGER) AS treated_d1,
        CAST(treated_d2 AS INTEGER) AS treated_d2,
        CAST(treated_d3 AS INTEGER) AS treated_d3,
        CAST(treated_d4 AS INTEGER) AS treated_d4,
        CAST(treated_d5 AS INTEGER) AS treated_d5,
        CAST(treated_d6 AS INTEGER) AS treated_d6,
        CAST(NULLIF(TRIM(treated_d7), '-') AS DOUBLE)             AS treated_pct_within_published,
        source_file,
        loaded_at
    FROM bronze_waitlist
)
SELECT
    t.snapshot_date,
    CASE WHEN t.snapshot_date <= DATE '2023-06-30' THEN 1 ELSE 3 END       AS period_months,
    CAST(date_trunc('month', t.snapshot_date)
         - to_months(CASE WHEN t.snapshot_date <= DATE '2023-06-30' THEN 0 ELSE 2 END)
         AS DATE)                                                          AS period_start,
    h.hhs_code,
    h.hhs_name,
    t.clinic_id,
    t.clinic_name_source,
    CASE WHEN t.clinic_id >= 900 THEN 'HHS' ELSE 'Clinic' END              AS report_level,
    t.list_name,
    l.list_group,
    l.target_months,
    l.within_target_bins,
    t.waiting_d1, t.waiting_d2, t.waiting_d3, t.waiting_d4, t.waiting_d5, t.waiting_d6,
    t.waiting_pct_within_published,
    t.treated_d1, t.treated_d2, t.treated_d3, t.treated_d4, t.treated_d5, t.treated_d6,
    t.treated_pct_within_published,
    COALESCE(t.waiting_pct_within_published > 100
             OR t.treated_pct_within_published > 100, FALSE)               AS flag_invalid_pct,
    t.source_file = '2023-september-quarter-oral-health.xlsx'              AS flag_includes_inquiry,
    t.hhs_name_source,
    t.hhs_code_source,
    t.source_file,
    t.loaded_at
FROM typed AS t
LEFT JOIN ref_hhs_alias AS h ON t.hhs_name_source = h.alias
LEFT JOIN ref_lists     AS l ON t.list_name = l.list_name;