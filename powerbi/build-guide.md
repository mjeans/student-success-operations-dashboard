# Power BI build guide

The repository includes Power BI-ready flat files, tested metric definitions,
DAX, a theme, and report specifications. A user with Power BI Desktop can build
and validate the interactive report. The generated SVG reports linked from the
README are a separate static implementation; no tested native Power BI report
is claimed here.

## Load the model

1. Run `python scripts/generate_data.py` to create ignored local fixtures.
2. Open Power BI Desktop and choose **Get data → Text/CSV**.
3. Load the seven files in `build/generated/`.
4. Assign dates and numeric types explicitly.
5. Create the relationships documented in `docs/data-model.md`.
6. Mark a date table if a dedicated calendar table is added.
7. Add the measures in `measures.dax`.
8. Import `theme.json` from **View → Themes → Browse for themes**.

## Proposed report pages

### 1. Executive overview

- KPI cards: eligible students, activation rate, dosage target rate,
  follow-up completion, paired score change, support SLA, high-risk schools
- Line chart: active rate and dosage rate by month
- Ranked bar chart: support SLA by district, with the 80% target visible
- Risk table: five highest-priority schools
- Slicers: region, district, implementation tier

### 2. Implementation monitor

- Matrix: school activation, dosage, follow-up, support, fidelity, freshness,
  exported scored flags, risk score and risk band
- Training rate and training-support flag displayed separately as context
- Action detail table with observed values, thresholds and suggested owners
- Slicers: district and risk band

### 3. Outcomes and participation

- KPI cards: cohort size, follow-up completion, missing follow-up, paired change
- Bar chart: within-student paired score change by grade
- Table: segment cohort size, follow-up completion, and paired score change
- Explicit noncausal interpretation and overlapping-segment notes

Do not substitute the difference of separate baseline/follow-up averages for
paired change when their observed samples differ. Label cohort size separately
from the paired-score denominator.

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

The current SVG previews are generated from the saved CSV outputs and checked
in CI. See [Visual design and reproduction](../docs/visual-design.md). The
original workbook and PNG images are unchanged. This guide is an interactive
report specification, not a claim of completed Power BI Desktop testing.

Official references:
https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview
https://learn.microsoft.com/en-us/power-bi/guidance/star-schema
https://learn.microsoft.com/en-us/power-bi/guidance/relationships-many-to-many
