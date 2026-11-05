# 6. Assumptions, data issues and discovery questions

## Assumptions log

| # | Assumption | Used in | Effect if wrong | Validate with |
|---|---|---|---|---|
| A1 | One GA dental episode costs the national efficient price for AR-DRG D40Z ($5,789) | Options B-D | Actual HHS cost could be higher (paediatric and complex adult cases) or lower (multiple short cases per session) | HHS costing team, local DRG cost |
| A2 | Inflow stays at the 2025 level (23.4 net additions a month) | Option C sizing | If referrals rise, extra capacity needed rises one-for-one | Referral trend from source system |
| A3 | Validation removes 0%, 10% or 20% of overdue patients | Option D | These are scenarios, not estimates. Each 10% is worth ~$470k | Pilot of 100 validation calls |
| A4 | Validation needs 1 AO4 for 6 months with a 25% on-cost loading ($64,732) | Option B | Small effect on the total case | HR and finance |
| A5 | Clinician re-triage time is absorbed in existing sessions | Option B | May displace chair time if not funded | Director of Oral Health |
| A6 | Extra capacity can be bought at 30-40 cases a month | Option D | If theatre or anaesthetist supply is the limit, timeline extends to 24 months or more | Perioperative services; private day hospital market sounding |

## Data issues found in the published files

Found while building the time series. Each one would be raised with the data custodian (opendata@health.qld.gov.au) in a real engagement.

| Issue | Impact on this analysis |
|---|---|
| Reporting moved from monthly to quarterly files from July 2023; "treated" covers one month before and three months after | Treated counts converted to a monthly rate before comparing |
| The July-September 2023 file includes "Inquiry" status in the waiting count; all other files count Waiting, Contacted and Appointment Made only | One quarter slightly overstated; noted, not adjusted |
| The January-March 2025 file says data is "current as at 12 November 2024", a date before the quarter it reports | Likely a template not updated; figures used as published |
| GA lists were reported per clinic until early 2024, then mostly as one line per HHS, then per clinic again in the December 2025 quarter | Analysis done at HHS level throughout so totals are consistent |
| HHS names appear as three-letter codes in some 2025 files, and Cape York / Torres Strait NPA appear separately in early files | Mapped to the 15 current HHS names |
| Removals from the list without treatment are not published | Net additions understate true referrals; list accuracy can't be assessed from public data |

## Discovery questions

**Oral health service**
1. How are GA categories assigned in practice? Is there a checklist, and who can override it?
2. What happens to a patient between referral and booking? Is there any scheduled contact?
3. How many patients were removed from the GA list without treatment in the last 12 months, and why?
4. How is the next patient chosen for a session: strict order, by clinic, by clinician?
5. What share of patients on the list are adults with additional needs, and do they follow a different pathway?

**Perioperative services**
6. How many dental GA sessions were allocated, used and cancelled in each of the last eight quarters, and why were they cancelled?
7. How many cases are done per session for children and for adults?
8. What caused the drop in throughput after mid-2023 (sessions, staffing, case mix)?
9. Is there capacity for extra sessions on weekends or in a private facility, and at what price?

**Performance and information**
10. Can the oral health information system extract additions, removals by reason and treatments by month?
11. Is a patient-level extract available for a validation pilot, under appropriate approvals?

**Wide Bay (benchmark)**
12. See the five questions in [section 4](04-root-cause.md#what-wide-bay-may-be-doing-differently).
