# 5. Requirements backlog

15 user stories across five epics, prioritised with MoSCoW and traced to the root causes in [section 4](04-root-cause.md) and the KPIs in [section 7](07-roadmap-kpis-risks.md). The full backlog with acceptance criteria is in [requirements_backlog.csv](requirements_backlog.csv), ready to import into Jira or Azure DevOps.

## Summary

| Epic | Must | Should | Root causes addressed |
|---|---|---|---|
| Worklist | 2 | 1 | 3. Not treated in turn; 6. Wasted sessions |
| Validation | 4 | | 4. Clinical change while waiting; 5. List not validated |
| Triage | 1 | 2 | 2. Category mix |
| Reporting | 3 | 1 | 1. Demand vs capacity; 2. Comparability |
| Data | 1 | | 5. Auditability |

## Examples

**WL-01 · Must · Worklist**
> As a booking officer, I want a weekly list of the next patients to book in clinical order, so that patients are treated in turn.
>
> - **Given** the GA list at the start of the week, **when** the worklist is generated, **then** patients are ordered by category (1, 2, 3) and then by days waited relative to target.
> - Any manual change to the order requires a reason code.

**VAL-04 · Must · Validation**
> As a waitlist officer, I want the system to block removal for "unable to contact" until three attempts on different days are logged, so that patients are not removed unfairly.
>
> - **Given** a patient with fewer than three logged attempts on separate days, **when** I select "unable to contact", **then** the removal is blocked with a message.

This story exists because validation programs create a risk of their own: removing vulnerable patients (often adults with disability, or families who have moved) because they didn't answer the phone. It protects patients and protects the HHS from complaints.

**RPT-01 · Must · Reporting**
> As the HHS Performance Unit, I want the share of patients waiting more than 12 months reported alongside % past target, so that performance is comparable across categories and HHSs.

## Non-functional requirements

| Area | Requirement |
|---|---|
| Privacy | Patient-level views restricted by clinic (row-level security). Compliant with the *Information Privacy Act 2009* (Qld) and Queensland Health information security policy |
| Source of truth | Reports read from the oral health information system, not from local spreadsheets. No re-keying |
| Refresh | Worklist and validation queue refreshed daily; performance reports monthly |
| Accessibility | WCAG 2.1 AA for any staff-facing screen |
| Definitions | KPI definitions documented in a data dictionary and match published Queensland Health definitions where one exists |

## Out of scope for the first release

- Patient-facing SMS or online portal for validation (logged as a future enhancement; depends on consent and contact data quality).
- Integration with private day hospital booking systems.
