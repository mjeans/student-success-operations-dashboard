# Power BI build guide

The repository includes Power BI-ready flat files, tested metric definitions,
DAX, a theme, and report specifications. Microsoft recommends PBIP for
source-controlled Power BI development; a user with Power BI Desktop can build
the report and save it as a PBIP project so the report and semantic model are
stored as text-based files.

## Load the model

1. Run `python scripts/generate_data.py` to create ignored local fixtures.
2. Open Power BI Desktop and choose **Get data → Text/CSV**.
3. Load the seven files in `build/generated/`.
4. Assign dates and numeric types explicitly.
5. Create the relationships documented in `docs/data-model.md`.
6. Mark a date table if a dedicated calendar table is added.
7. Add the measures in `measures.dax`.
8. Import `theme.json` from **View → Themes → Browse for themes**.

## Report pages

### 1. Executive overview

- KPI cards: eligible students, activation rate, dosage target rate,
  follow-up completion, average score change, support SLA, high-risk schools
- Line chart: active rate and dosage rate by month
- Ranked bar chart: activation rate by district
- Risk table: five highest-priority schools
- Slicers: region, district, implementation tier

### 2. Implementation monitor

- Matrix: school-by-school activation, dosage, follow-up, support, training,
  fidelity, freshness, and risk band
- Scatter plot: training rate versus activation rate, sized by students and
  colored by risk band
- Bar chart: support SLA by district
- Slicers: district and risk band

### 3. Outcomes and participation

- KPI cards: average baseline, follow-up, and score change
- Clustered bar chart: baseline and follow-up by grade
- Table: segment sample size, follow-up completion, and score change
- Explicit noncausal interpretation note

## Verification

Reconcile the report-level totals to `outputs/02_dashboard_kpis.csv`. The report
should show 3,200 eligible students, 92.1% 60-day activation, 67.7% dosage
target attainment, 89.6% follow-up completion, +9.71 average score change,
68.1% support SLA attainment, and five high-risk schools.

PBIP must be created or converted through Power BI Desktop; Microsoft does not
support programmatic PBIX/PBIP conversion. This repository therefore avoids
claiming that a hand-authored binary PBIX was validated.

Official reference:
https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview
