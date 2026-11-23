-- Gold: tables designed to answer business questions. This is what the language model sees.

-- 1. One row per waiting list
CREATE OR REPLACE TABLE dim_list AS
SELECT
    list_name,
    list_group,
    CAST(target_months AS INTEGER) AS target_months,
    CASE list_name
        WHEN 'Clinical Assessment' THEN 'Assessment to decide whether priority treatment is needed'
        WHEN 'General' THEN 'Routine check-up and general dental treatment'
        ELSE 'Dental treatment'
             || CASE WHEN list_group = 'General anaesthetic' THEN ' under general anaesthetic' ELSE '' END
    END AS list_description
FROM ref_lists;

-- 2. One row per clinic, with the name used in its most recent snapshot
CREATE OR REPLACE TABLE dim_clinic AS
SELECT
    clinic_id,
    arg_max(clinic_name_source, snapshot_date) AS clinic_name,
    arg_max(hhs_code, snapshot_date)           AS hhs_code,
    arg_max(hhs_name, snapshot_date)           AS hhs_name,
    clinic_id >= 900                           AS is_hhs_level_ga_record,
    MIN(snapshot_date)                         AS first_snapshot,
    MAX(snapshot_date)                         AS last_snapshot
FROM silver_waitlist
GROUP BY clinic_id;

-- 3. One row per snapshot, clinic and list, with the measures already calculated
CREATE OR REPLACE TABLE fact_waitlist AS
SELECT
    s.snapshot_date,
    s.period_start,
    s.period_months,
    s.hhs_code,
    s.hhs_name,
    s.clinic_id,
    s.report_level,
    s.list_name,
    s.list_group,
    s.target_months,
    s.waiting_d1 + s.waiting_d2 + s.waiting_d3 + s.waiting_d4 + s.waiting_d5 + s.waiting_d6
        AS waiting_total,
    s.waiting_d1 + CASE WHEN s.within_target_bins = 2 THEN s.waiting_d2 ELSE 0 END
        AS waiting_within_target,
    s.waiting_d1 + s.waiting_d2 + s.waiting_d3 + s.waiting_d4 + s.waiting_d5 + s.waiting_d6
        - (s.waiting_d1 + CASE WHEN s.within_target_bins = 2 THEN s.waiting_d2 ELSE 0 END)
        AS waiting_past_target,
    s.treated_d1 + s.treated_d2 + s.treated_d3 + s.treated_d4 + s.treated_d5 + s.treated_d6
        AS treated_in_period,
    s.treated_d1 + CASE WHEN s.within_target_bins = 2 THEN s.treated_d2 ELSE 0 END
        AS treated_within_target,
    ROUND((s.treated_d1 + s.treated_d2 + s.treated_d3 + s.treated_d4 + s.treated_d5 + s.treated_d6)
          / s.period_months, 2)
        AS treated_per_month,
    s.flag_includes_inquiry AS includes_inquiry_status
FROM silver_waitlist AS s;

-- 4. Long format: one row per snapshot, clinic, list and months-waited band
CREATE OR REPLACE TABLE fact_wait_band AS
WITH bands AS (
    SELECT s.*, b.band, l.band_width_months
    FROM silver_waitlist AS s
    CROSS JOIN range(1, 7) AS b(band)
    JOIN ref_lists AS l USING (list_name)
)
SELECT
    snapshot_date,
    hhs_code,
    hhs_name,
    clinic_id,
    report_level,
    list_name,
    CAST(band AS INTEGER)                                         AS band_order,
    CAST((band - 1) * band_width_months AS INTEGER)               AS months_waited_from,
    CASE WHEN band < 6 THEN CAST(band * band_width_months AS INTEGER) END
                                                                  AS months_waited_to,
    CASE WHEN band < 6
         THEN CAST((band - 1) * band_width_months AS INTEGER) || ' to '
              || CAST(band * band_width_months AS INTEGER) || ' months'
         ELSE 'over ' || CAST((band - 1) * band_width_months AS INTEGER) || ' months'
    END                                                           AS band_label,
    band > within_target_bins                                     AS is_past_target,
    CASE band WHEN 1 THEN waiting_d1 WHEN 2 THEN waiting_d2 WHEN 3 THEN waiting_d3
              WHEN 4 THEN waiting_d4 WHEN 5 THEN waiting_d5 ELSE waiting_d6 END  AS waiting,
    CASE band WHEN 1 THEN treated_d1 WHEN 2 THEN treated_d2 WHEN 3 THEN treated_d3
              WHEN 4 THEN treated_d4 WHEN 5 THEN treated_d5 ELSE treated_d6 END  AS treated_in_period
FROM bands;