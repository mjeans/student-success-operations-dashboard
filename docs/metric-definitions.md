# Metric definitions

The dashboard separates participation, dosage, outcome completeness, outcomes,
and implementation conditions. These measures answer different questions and
should not be interpreted interchangeably.

| Metric | Definition | Grain | Target | Caveat |
|---|---|---|---:|---|
| Eligible students | Distinct students in the synthetic enrollment dimension | Student | — | Denominator is fixed at the generated cohort |
| 60-day activation rate | Share of students with any activity in September or October 2025 | Student | 75% | Activation does not imply sustained use |
| Dosage target rate | Share of student-months with at least 60 minutes of use | Student-month | 60% | A month below 60 minutes is not necessarily a program failure |
| Follow-up completion rate | Share of students with a valid follow-up assessment | Student | 80% | Missing outcomes may be systematically different |
| Average score change | Mean follow-up minus baseline score among students with both assessments | Student | Positive | Descriptive; no untreated counterfactual is present |
| Support SLA rate | Share of support tickets with an initial response within 24 hours | Ticket | 80% | Ticket complexity is not risk-adjusted |
| Training rate | Staff trained divided by staff expected | School | 80% | Does not measure training quality |
| Fidelity score | Synthetic implementation rubric scored from 0–100 | School | 70 | Intended for prioritization, not personnel evaluation |
| Data freshness | Days since the school data feed last refreshed | School | ≤14 days | Stale data can distort every downstream metric |
| Risk score | Count of six thresholds missed: activation, dosage, follow-up, support SLA, fidelity, freshness | School | <3 | Equal weights make the logic transparent but are not empirically optimized |

## Risk bands

- **Critical:** four or more thresholds missed
- **High:** three thresholds missed
- **Watch:** two thresholds missed
- **Stable:** zero or one threshold missed

The risk score is an operational triage rule. It is not a predictive model and
should be combined with local context before resources are reassigned.

## Driver drill-down and contextual indicators

The risk export appends `missed_activation_target`, `missed_dosage_target`,
`missed_followup_target`, `missed_support_sla_target`, `missed_fidelity_target`
and `stale_data_flag`. Their sum must equal `risk_score` for every school.
Comparisons use unrounded values; equality meets the target.

`training_support_needed` marks training below 80% but does not enter the score.
The action queue contains one row per school and failed scored driver; training
and stale-data context accompany those rows. Training-only cases can be found
in the school-level table, without inventing another score component.

See [Action queue rules and interpretation](action-queue.md) for routing, mixed
units, suggested cadences, missing-data caveats and reporting at the correct
grain. The original score, bands, rankings and existing metric columns are
protected by a frozen-baseline regression test.
