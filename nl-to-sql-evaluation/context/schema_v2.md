# Database schema (DuckDB) with documentation

## dim_list
The eight public dental waiting lists and their clinically recommended waiting times.
Grain: One row per waiting list.

- list_name (VARCHAR): Name of the waiting list. Join key to the fact tables.
- list_group (VARCHAR): Group of lists: Assessment, General care, Priority or General anaesthetic.
- target_months (INTEGER): Clinically recommended maximum wait, in months. Patients waiting longer are past target.
- list_description (VARCHAR): Plain-English description of what the list is for.

## dim_clinic
Public dental clinics in Queensland, with the Hospital and Health Service (HHS) they belong to.
Grain: One row per clinic_id.

- clinic_id (INTEGER): Stable clinic identifier. Use this, not the name, to identify a clinic over time.
- clinic_name (VARCHAR): Clinic name as shown in the most recent snapshot. Names were sometimes abbreviated or changed in older files.
- hhs_code (VARCHAR): Three-letter code of the Hospital and Health Service (e.g. MST = Metro South).
- hhs_name (VARCHAR): Name of the Hospital and Health Service.
- is_hhs_level_ga_record (BOOLEAN): True for clinic_id 901-915. These are not real clinics: they hold general anaesthetic lists reported for a whole HHS.
- first_snapshot (DATE): First snapshot date in which the clinic appears.
- last_snapshot (DATE): Last snapshot date in which the clinic appears.

## fact_waitlist
Waiting list size and patients treated, by snapshot date, clinic and waiting list.
Grain: One row per snapshot_date, clinic_id and list_name.

- snapshot_date (DATE): Date the waiting list was counted (last day of a month or quarter).
- period_start (DATE): First day of the period that treated_in_period covers.
- period_months (INTEGER): Length of the reporting period in months. 1 until June 2023 (monthly releases), 3 from July 2023 (quarterly releases).
- hhs_code (VARCHAR): Three-letter code of the Hospital and Health Service.
- hhs_name (VARCHAR): Name of the Hospital and Health Service.
- clinic_id (INTEGER): Clinic identifier. Join key to dim_clinic.
- report_level (VARCHAR): 'Clinic' for a real clinic. 'HHS' for general anaesthetic lists reported for a whole HHS (clinic_id 901-915).
- list_name (VARCHAR): Waiting list. Join key to dim_list.
- list_group (VARCHAR): Group of lists: Assessment, General care, Priority or General anaesthetic.
- target_months (BIGINT): Clinically recommended maximum wait for this list, in months.
- waiting_total (INTEGER): People on the waiting list at snapshot_date.
- waiting_within_target (INTEGER): People waiting who have not yet passed the recommended time.
- waiting_past_target (INTEGER): People waiting longer than the recommended time.
- treated_in_period (INTEGER): People treated from the list during the reporting period (period_start to snapshot_date).
- treated_within_target (INTEGER): People treated during the period who were treated within the recommended time.
- treated_per_month (DOUBLE): treated_in_period divided by period_months. Use this to compare treatment volumes across monthly and quarterly periods.
- includes_inquiry_status (BOOLEAN): True for the September 2023 quarter only, when people with an 'Inquiry' status were also counted as waiting. Waiting counts for that snapshot may be slightly higher.

## fact_wait_band
Waiting list split by how long people have waited, in months. Same people as fact_waitlist, broken down by wait band.
Grain: One row per snapshot_date, clinic_id, list_name and wait band (6 bands per list).

- snapshot_date (DATE): Date the waiting list was counted.
- hhs_code (VARCHAR): Three-letter code of the Hospital and Health Service.
- hhs_name (VARCHAR): Name of the Hospital and Health Service.
- clinic_id (INTEGER): Clinic identifier. Join key to dim_clinic.
- report_level (VARCHAR): 'Clinic' or 'HHS' (see fact_waitlist).
- list_name (VARCHAR): Waiting list. Join key to dim_list.
- band_order (INTEGER): Order of the band, 1 (shortest wait) to 6 (longest).
- months_waited_from (INTEGER): Lower bound of the band, in months (exclusive, except 0).
- months_waited_to (INTEGER): Upper bound of the band, in months (inclusive). NULL for the last, open-ended band.
- band_label (VARCHAR): Readable label, e.g. '12 to 18 months' or 'over 30 months'.
- is_past_target (BOOLEAN): True if everyone in this band has waited longer than the recommended time.
- waiting (INTEGER): People waiting in this band at snapshot_date.
- treated_in_period (INTEGER): People treated during the period whose wait fell in this band.

## Clinical background
- Priority lists hold patients assessed as needing treatment sooner because of their oral health need, for example pain or infection. Clinical Assessment is the step that decides this.
- General anaesthetic lists usually include young children with extensive decay and people who cannot be treated in the dental chair, for example because of disability.
- This is clinical context only. The data does not record any patient characteristics, so it cannot be used to count or label patients by type.

## Rules
1. Waiting counts are snapshots. To answer "how many are waiting", filter to one snapshot_date (the latest, MAX(snapshot_date), unless a date is given). Never add waiting counts across snapshot dates.
2. Treated counts are flows over the reporting period. They can be added across snapshot dates to cover a longer span. To compare periods of different length, use treated_per_month.
3. A percentage across several rows is a ratio of sums, e.g. 100.0 * SUM(waiting_past_target) / SUM(waiting_total). Do not average row-level percentages.
4. Different lists have different targets, so "% past target" is not directly comparable between lists or between groups with a different mix of lists. To compare wait length on equal terms, use fact_wait_band and a fixed number of months (e.g. months_waited_from >= 12).
5. The 'General' list (routine care, 24-month target) is not the same as the 'General anaesthetic' lists.
6. General anaesthetic lists are reported per HHS (report_level = 'HHS') from December 2023 to September 2025, and per clinic before and after. Totals by HHS or for Queensland are correct in all periods; clinic-level general anaesthetic figures are not available for that period.
7. There is no general anaesthetic data after 31 December 2025. For general anaesthetic questions, the latest snapshot is the latest date that has general anaesthetic rows, not the overall latest date.
8. Dates in questions refer to snapshot_date. A financial year runs 1 July to 30 June; "2024-25" means July 2024 to June 2025.

## Not available in this data
- Patient age, or whether patients are children or adults.
- New referrals or additions to the list, and removals without treatment.
- Reasons for waiting, costs, staffing or appointment details.
- Any data before July 2021.
- Medical conditions, diagnoses, disability status or reason for referral. The data has counts of people only, with no patient-level information.
- Hospital theatre capacity, anaesthetist availability or any other cause of delay. The data shows how long people wait, not why.
If a question needs information that is not available, say so instead of answering.