# Data exploration notes: Queensland public dental waiting lists

Source: Queensland Health, public dental waiting lists, data.qld.gov.au
Files reviewed: 36 releases, July 2021 to June 2026 (monthly to June 2023, quarterly from July 2023)
Checked with Python (openpyxl) across all 36 files on 23 Nov 2026.

**Source tags**
- **[Source: Notes]** taken from the official Notes sheet in each file
- **[Verified]** confirmed by checking all 36 files
- **[Inferred]** my interpretation, not stated in the source and not testable from the data

## 1. What does one row represent? (grain)

One row = one **clinic** + one **waiting list (Area)** + one **snapshot date**. [Verified: each file has a single snapshot date, and no file has two rows with the same date, clinic and list]

The date is the last day of the reporting month or quarter, not a day of service. Dates are stored as real Excel dates. [Verified]

Columns, July 2021 to December 2025: `date`, `clinicID`, `clinicName`, `Hospital and Health Service`, `Area`, `Waiting D1` to `Waiting D7`, `Treated D1` to `Treated D7`. [Verified]

**Schema change in 2026:** the March and June 2026 files rename the first columns (`Date`, `ClinicID`, `ClinicName`), add a new column `HHS_ID` (three-letter code), name the data sheet after the file instead of "Data", and write clinic names in title case instead of upper case. [Verified]

All data is preliminary and subject to change. [Source: Notes]

## 2. Waiting lists (Area) and clinical targets

There are 8 lists. Each has a recommended (desirable) time to treatment. [Source: Notes]

| List (Area) | What it is | Recommended time |
|---|---|---|
| Clinical Assessment | Assessment to determine need for priority treatment | 1 month |
| General | Routine check-up and dental treatment | 24 months |
| Priority 1 | Dental treatment | 1 month |
| Priority 2 | Dental treatment | 3 months |
| Priority 3 | Dental treatment | 12 months |
| General Anaesthetic Category 1 | Dental treatment under general anaesthetic | 1 month |
| General Anaesthetic Category 2 | Dental treatment under general anaesthetic | 3 months |
| General Anaesthetic Category 3 | Dental treatment under general anaesthetic | 12 months |

**The 2026 files contain no General Anaesthetic rows**, although their Notes sheet still defines the three GA lists. The last GA data is December 2025. [Verified]

## 3. Waiting D1 to D6

Number of people, grouped by **months waited**. The month ranges are different for each list. [Source: Notes]

| List | D1 | D2 | D3 | D4 | D5 | D6 |
|---|---|---|---|---|---|---|
| Clinical Assessment, Priority 1, GA Cat 1 | up to 1 | >1 to 2 | >2 to 3 | >3 to 4 | >4 to 5 | > 5 |
| Priority 2, GA Cat 2 | up to 3 | >3 to 6 | >6 to 9 | >9 to 12 | >12 to 15 | > 15 |
| Priority 3, GA Cat 3 | up to 6 | >6 to 12 | >12 to 18 | >18 to 24 | >24 to 30 | > 30 |
| General | up to 12 | >12 to 24 | >24 to 36 | >36 to 48 | >48 to 60 | > 60 |

- Most files label the ranges "< 3", "4 to 6", which leaves gaps. The September 2023 quarter file uses "<= 3", ">3 to 6", which closes them; the table above uses that wording. [Source: Notes, September 2023 file]
- Because the ranges differ, "D2" does not mean the same thing across lists. D columns must not be compared or added across lists without converting to months. [Inferred]
- Within the recommended time: **D1** for 1-month and 3-month lists; **D1 + D2** for 12-month and 24-month lists. Everything after is past the recommended time. [Verified: this rule reproduces the published Waiting D7 within 1 percentage point in about 97% of rows]
- All D1 to D6 values are whole numbers. [Verified]

## 4. D7

D7 is a **percentage**, not a count: "% within recommended waiting time". [Source: Notes]
- **Waiting D7:** % of people currently waiting who are still within the recommended time.
- **Treated D7:** % of people treated in the period who were treated within the recommended time.

D1 to D6 are counts of people, but D7 is a percentage. **D7 must never be added to D1-D6.** [Inferred]

One impossible value: Torres Strait Dental Clinic, General list, September 2022 has Waiting D7 = 258. Recalculated from D1-D6 it should be about 91. [Verified]

## 5. Waiting vs Treated

- **Waiting** is a **snapshot (stock)**: people on the list at the snapshot date, with status Waiting, Contacted or Appointment Made. [Source: Notes]
- **Treated** is a **flow**: people treated from the list during the reporting period. [Source: Notes]

Consequence [Inferred]:
- Treated can be added over time (e.g. four quarters = one year).
- Waiting **cannot** be added over time: adding snapshots counts the same person several times. To describe a year, use one snapshot (e.g. year end) or an average.

## 6. Monthly vs quarterly files

- July 2021 to June 2023: monthly files; Treated covers one month. From July 2023: quarterly files; Treated covers three months. [Verified from the "Visit Dates are from ... to ..." line in each Notes sheet]
- Waiting is a snapshot in both formats, so it can be compared across them.
- Treated is only comparable after converting to a monthly rate (quarterly Treated / 3). [Inferred]

## 7. Anomalies and open questions

| # | Observation | Tag |
|---|---|---|
| 7.1 | "-" means "data not available or not applicable". It is not zero and must be loaded as NULL. It only appears in the two D7 columns. | [Source: Notes] [Verified] |
| 7.2 | General Anaesthetic lists are reported per clinic until September 2023, as about one row per HHS from December 2023 to September 2025, and per clinic again in December 2025. Clinic-level GA analysis is not possible for that middle period. | [Verified] |
| 7.3 | Two files have a "data current as at" date before the end of the quarter they report: December 2024 quarter and March 2025 quarter (both say 12 November 2024). Probably a template not updated. | [Verified] |
| 7.4 | The September 2023 quarter file counts the status "Inquiry" as waiting; all other files count only Waiting, Contacted and Appointment Made. That quarter may be slightly overstated. | [Verified] |
| 7.5 | In the June 2025 quarter file, the GA rows use three-letter HHS codes (e.g. MST, WBY) while all other rows use full names. Needs mapping to one name. | [Verified] |
| 7.6 | From October 2022 to April 2023, some rows use "Cape York" and "Torres Strait NPA" as the HHS name, alongside "Torres and Cape". Both belong to the Torres and Cape HHS. | [Verified] |
| 7.7 | One impossible D7 value (258), see section 4. | [Verified] |
| 7.8 | General Anaesthetic lists are missing from the 2026 files. | [Verified] |
| 7.9 | Not published: additions to the list, removals without treatment, patient age group. Questions that need these cannot be answered from this data. | [Verified: no such columns in any file] |
| 7.10 | The published D7 is wrong in most rows of two files: Waiting D7 in April 2022 (249 of 310 rows) and Treated D7 in May 2022 (115 of 308 rows). In the other 33 files, the within-target rule reproduces D7 in every row. Decision: gold recalculates percentages from D1-D6 and never uses the published D7. | [Verified] |
