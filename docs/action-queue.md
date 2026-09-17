# Implementation-risk action queue

## Decision and grain

The queue answers: **Which operating condition needs attention at each school,
and which team should investigate first?** It contains one row per school and
failed **scored** driver. It is a proposed triage aid, not a validated prediction,
a causal explanation, a record of assigned work, or a service-level commitment.
All records and school names are synthetic.

`sql/01_risk_views.sql` contains one rule catalog for thresholds, driver order,
labels and suggested routing. The school risk export, executive high-risk count
and action queue use the same scored view. Decisions and ranking use unrounded
values; the original school export keeps its existing display precision.

## Rules and routing

| Order | Driver code | Flag condition | Suggested owner |
|---|---|---|---|
| 1 | ACTIVATION | Activation < 0.75 | School-success lead |
| 2 | DOSAGE | Dosage attainment < 0.60 | Implementation lead |
| 3 | FOLLOWUP | Follow-up completion < 0.80 | Assessment lead |
| 4 | SUPPORT_SLA | Response-within-24-hours rate < 0.80 | Support operations |
| 5 | FIDELITY | Fidelity score < 70 | Implementation lead |
| 6 | DATA_FRESHNESS | Refresh age > 14 days | Data operations |

Equality meets each target: 75% activation, 60% dosage, 80% follow-up, 80%
support response, fidelity 70 and freshness 14 days do not trigger their flags.
Rates in the CSV are proportions, not percentages. Fidelity is a 0-100 score;
freshness is measured in days. Do not average or sum observed values across
these different units. A rounded display may look equal to a target while the
unrounded value is just below it; inspect the queue value for the decision.

`risk_score` is the sum of the six binary driver flags. Risk bands and ordering
are unchanged: Critical >=4, High =3, Watch =2, Stable =0 or 1; rank by score
descending, unrounded activation ascending, then school ID. The action queue
sorts by intervention priority, school ID and the documented driver order.
A Stable school with one missed target still has one action row.

## Training is context, not another score component

`training_support_needed = 1` when the training rate is below 80%. Training rate
and this flag accompany every action, but training adds **no point** and creates
**no extra scored row**. For a fidelity or dosage action, a low training flag is
a prompt for the implementation lead to investigate support needs, not proof
that training caused the shortfall. Training-only cases remain visible by
filtering the school-level risk table on this flag; they are not inserted into
the scored action queue.

## Suggested cadence and stale data

The illustrative review cadence is twice weekly for Critical, weekly for High,
every two weeks for Watch, and monthly for Stable. These are proposed defaults
for a team to approve or replace with its capacity and local context. They are
not empirically calibrated deadlines, elapsed response times, or promises.

`stale_data_flag` accompanies every action for the school. Verify the feed
before interpreting other flagged metrics when it is set; all flagged drivers
remain in the queue rather than disappearing behind one generic recommendation.
The driver order is a stable display order, not a claim about causal importance.

## Inspect and reproduce

- `outputs/06_implementation_risk.csv`: one row per school, with the original
  columns preserved and seven flags appended (six scored, one contextual).
- `outputs/08_intervention_action_queue.csv`: one row per school and failed
  driver, including school sample size, observed value, threshold, units,
  operator, suggested first action, owner, cadence and context.
- `tests/fixtures/implementation_risk_baseline.csv`: frozen original export from
  commit `00f662da0093cee6c4a2317f9399c46ccab3f627`; do not regenerate this baseline
  from the new code to make a failing comparison pass.

Rebuild the database after updating the repository so the new views exist:

```bash
python scripts/generate_data.py
python scripts/build_database.py
python scripts/run_queries.py
python scripts/render_previews.py
python -m unittest discover -s tests -v
```

The reference data produce 40 scored actions across 21 schools. Summit Plains
School 4 has five: dosage, follow-up, support response, fidelity and freshness.
Its 50% training rate supplies context without changing its score of five.
An empty action queue is exported as a header-only CSV, not a blank file.

## Interpretation and reporting limits

The queue preserves the existing metric population, denominators and handling
of missingness; it does not add a new data-completeness model. In particular,
the upstream view treats schools with no support tickets as having a support
rate of 1.0 for scoring, not as evidence of observed good service. Null metrics
are not counted as missed thresholds under the inherited CASE rules. Existing
quality checks and local review remain necessary.

School sample sizes and risk scores repeat across action rows. Never sum those
repeated fields to report students served or overall school risk. Use the
school-grain table for school/student summaries and count distinct school IDs
for schools represented in the queue. The Power BI build guide specifies the
separate grains and filtering path.

The current implementation-monitor SVG displays scored drivers and suggested
owners from these outputs. See [Visual design and reproduction](visual-design.md).
The original PNG files and Excel workbook remain unchanged. The static SVG
reports do not claim a completed or tested native Power BI report.
