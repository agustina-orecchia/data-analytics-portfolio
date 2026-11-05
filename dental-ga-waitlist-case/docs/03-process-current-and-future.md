# 3. Current and future state process

The current state is reconstructed from Queensland Health's published waiting list definitions and how public dental GA services generally operate. It has not been walked through with Metro South staff. Pain points marked **(H)** are hypotheses to test in discovery; those marked **(D)** are supported by the published data.

## Current state: referral to treatment

```mermaid
flowchart LR
    subgraph Referrer
        A[Dental examination<br/>at community or<br/>school clinic] --> B{Treatable in<br/>the chair?}
    end
    subgraph Oral_health_service[Oral health service]
        B -- No --> C[GA referral<br/>completed]
        C --> D[Clinician assigns<br/>GA category 1, 2 or 3]
        D --> E[(Added to GA<br/>waiting list)]
        E --> F[Patient waits.<br/>No scheduled contact]
        F --> G[Booking officer<br/>picks next patient]
    end
    subgraph Perioperative
        G --> H[Pre-anaesthetic<br/>assessment]
        H --> I{Session<br/>available?}
        I -- No --> F
        I -- Yes --> J[Treatment<br/>under GA]
    end
    J --> K[Removed from list.<br/>Review appointment]
    B -- Yes --> L[Treated in<br/>community clinic]
```

| Step | Pain point |
|---|---|
| D. Categorisation | Category mix differs sharply between HHSs: 83% Category 2 in Metro South, 0% in Wide Bay **(D)**. Criteria are likely applied differently by individual clinicians **(H)** |
| E-F. Waiting | No scheduled contact while waiting, so changes in address, need or symptoms are not picked up **(H)**. Removals without treatment are not reported publicly, so list accuracy is unknown **(D)** |
| G. Selection | Unclear whether patients are booked in turn (category, then time waited) or by clinician or clinic availability **(H)**. Only 23% of Metro South patients treated in 2025 were treated within target **(D)** |
| H. Pre-anaesthetic | Assessment done late, close to the theatre date, so a failed assessment leaves an empty slot **(H)** |
| I. Sessions | Dental shares theatre sessions with other specialties; lost or cancelled sessions are not backfilled **(H)**. Throughput fell from ~450 to ~360 patients a year between mid-2023 and 2025 **(D)** |

## Future state

```mermaid
flowchart LR
    subgraph Referrer
        A[Dental examination] --> B{Treatable in<br/>the chair?}
    end
    subgraph Oral_health_service[Oral health service]
        B -- No --> C[GA referral with<br/>structured triage<br/>checklist]
        C --> D[Category assigned<br/>against statewide<br/>criteria]
        D --> E[(GA waiting list)]
        E --> V[90-day validation<br/>contact]
        V -- Still needs GA --> E
        V -- Need changed --> R[Clinical<br/>re-triage]
        R --> E
        V -- No longer needed --> X[Removed with<br/>reason code]
        E --> W[Weekly worklist:<br/>treat in turn]
        W --> P[Pre-anaesthetic<br/>assessment booked<br/>at 60 days before<br/>expected date]
    end
    subgraph Perioperative
        P --> S[Session filled<br/>from worklist plus<br/>short-notice pool]
        S --> J[Treatment<br/>under GA]
        S -. Cancellation .-> Q[Backfill from<br/>short-notice pool]
        Q --> J
    end
    J --> K[Removed with<br/>outcome recorded]
```

## What changes

| Change | Addresses | Owner |
|---|---|---|
| Structured triage checklist at referral, audited quarterly | Inconsistent categorisation | Senior dentist |
| 90-day validation contact with scripted call and reason codes | Stale list, unreported deterioration | Waitlist officer |
| Weekly treat-in-turn worklist (see prototype) | Patients not booked in clinical order | Booking officer |
| Pre-anaesthetic assessment brought forward | Empty slots from failed assessments | Perioperative nurse |
| Short-notice pool of assessed patients who can come in at 48 hours' notice | Lost sessions after cancellations | Booking officer |
| Removal reason codes captured and reported | Unknown list accuracy | Oral health information team |
