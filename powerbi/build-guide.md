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

### 4. Implementation action queue (SQL/CSV extension)

Rebuild the SQLite database and run `scripts/run_queries.py` after generation.
Import `outputs/06_implementation_risk.csv` and
`outputs/08_intervention_action_queue.csv`; name the latter `action_queue`.

In Power Query, merge the school-level risk export into `dim_school` by
`school_id`, retaining one row per school. Expand the priority, risk score,
band, metric values and seven flags. Check that the merge still has 32 unique
school IDs; do not join the action rows into the school dimension.

Relate `dim_school[school_id]` (one) to `action_queue[school_id]` (many), with
single-direction filtering from the school dimension. Retain the existing
district-to-school path. Do not add a second active district-to-queue path or
join the queue directly to student-level fact tables. Use school/district/risk
band fields from the dimensions for slicers and drillthrough.

The page should show school, risk band, driver label, observed value, target,
unit, first action, suggested owner, suggested cadence and training context.
Sort by intervention priority, school ID and driver order. Show rate values as
percentages, fidelity as a score and refresh age as days. Preserve raw precision
in a tooltip when rounding would conceal a near-threshold failure.

Count rows for actions and distinct school IDs for schools with scored actions.
Never sum `students` or `risk_score` over the action table: these school-level
values repeat for each driver. Use the school dimension for school-grain
summaries. A separate school table filtered on `training_support_needed = 1`
keeps training-only cases visible without adding a seventh scored action.

Label the page **Operational triage — synthetic data; not a validated
prediction**. Show a stale-data warning for flagged schools. Suggested ownership
and cadence are proposals, not assignments or commitments. See
[Action queue rules](../docs/action-queue.md).

## Verification

Reconcile the report-level totals to `outputs/02_dashboard_kpis.csv`. The report
should show 3,200 eligible students, 92.1% 60-day activation, 67.7% dosage
target attainment, 89.6% follow-up completion, +9.71 average score change,
68.1% support SLA attainment, and five high-risk schools.

The new queue should show 40 action rows across 21 schools. Drilling through
Summit Plains School 4 should show exactly five scored drivers and low-training
context. A training-only school should remain visible in the school table,
not appear as a fabricated scored action.

PBIP must be created or converted through Power BI Desktop; Microsoft does not
support programmatic PBIX/PBIP conversion. This repository therefore avoids
claiming that a hand-authored binary PBIX was validated. The existing workbook
and preview images are unchanged; the new page is specified here, not claimed
as tested in Power BI Desktop.

Official references:
https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview
https://learn.microsoft.com/en-us/power-bi/guidance/star-schema
https://learn.microsoft.com/en-us/power-bi/guidance/relationships-many-to-many
