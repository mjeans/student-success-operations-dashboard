-- One inspectable rule catalog supplies thresholds, driver order and routing.
-- Recommendations are illustrative operating guidance, not validated predictions.
DROP VIEW IF EXISTS v_school_implementation_risk;
DROP VIEW IF EXISTS v_school_risk_drivers;
DROP VIEW IF EXISTS v_implementation_driver_rules;

CREATE VIEW v_implementation_driver_rules AS
WITH rules (
    driver_order, driver_code, driver_label, target_value, metric_unit,
    failure_operator, recommended_first_action, suggested_owner
) AS (
    VALUES
    (1, 'ACTIVATION', '60-day activation', 0.75, 'proportion', '<',
     'Review access barriers and the onboarding workflow.', 'School-success lead'),
    (2, 'DOSAGE', 'Dosage target attainment', 0.60, 'proportion', '<',
     'Review usage schedules and barriers to sustained participation.', 'Implementation lead'),
    (3, 'FOLLOWUP', 'Follow-up completion', 0.80, 'proportion', '<',
     'Reconcile missing assessments and plan follow-up collection.', 'Assessment lead'),
    (4, 'SUPPORT_SLA', 'Support response within 24 hours', 0.80, 'proportion', '<',
     'Review the ticket backlog, staffing and escalation coverage.', 'Support operations'),
    (5, 'FIDELITY', 'Implementation fidelity', 70.0, 'score', '<',
     'Observe delivery and agree a targeted coaching plan.', 'Implementation lead'),
    (6, 'DATA_FRESHNESS', 'Days since data refresh', 14.0, 'days', '>',
     'Verify and restore the data feed before interpreting stale metrics.', 'Data operations')
)
SELECT * FROM rules;

CREATE VIEW v_school_risk_drivers AS
WITH observed AS (
    SELECT
        som.school_id,
        rules.*,
        CASE rules.driver_code
            WHEN 'ACTIVATION' THEN som.activation_rate
            WHEN 'DOSAGE' THEN som.dosage_rate
            WHEN 'FOLLOWUP' THEN som.followup_rate
            WHEN 'SUPPORT_SLA' THEN som.support_sla_rate
            WHEN 'FIDELITY' THEN som.fidelity_score
            WHEN 'DATA_FRESHNESS' THEN som.data_refresh_days
        END AS observed_value
    FROM v_school_operating_metrics AS som
    CROSS JOIN v_implementation_driver_rules AS rules
)
SELECT
    observed.*,
    CASE
        WHEN failure_operator = '<' AND observed_value < target_value THEN 1
        WHEN failure_operator = '>' AND observed_value > target_value THEN 1
        ELSE 0
    END AS target_missed
FROM observed;

CREATE VIEW v_school_implementation_risk AS
WITH flags AS (
    SELECT
        school_id,
        MAX(CASE WHEN driver_code = 'ACTIVATION' THEN target_missed ELSE 0 END)
            AS missed_activation_target,
        MAX(CASE WHEN driver_code = 'DOSAGE' THEN target_missed ELSE 0 END)
            AS missed_dosage_target,
        MAX(CASE WHEN driver_code = 'FOLLOWUP' THEN target_missed ELSE 0 END)
            AS missed_followup_target,
        MAX(CASE WHEN driver_code = 'SUPPORT_SLA' THEN target_missed ELSE 0 END)
            AS missed_support_sla_target,
        MAX(CASE WHEN driver_code = 'FIDELITY' THEN target_missed ELSE 0 END)
            AS missed_fidelity_target,
        MAX(CASE WHEN driver_code = 'DATA_FRESHNESS' THEN target_missed ELSE 0 END)
            AS stale_data_flag,
        SUM(target_missed) AS risk_score
    FROM v_school_risk_drivers
    GROUP BY school_id
)
SELECT
    RANK() OVER (
        ORDER BY flags.risk_score DESC, som.activation_rate ASC, som.school_id
    ) AS intervention_priority,
    som.*,
    flags.missed_activation_target,
    flags.missed_dosage_target,
    flags.missed_followup_target,
    flags.missed_support_sla_target,
    flags.missed_fidelity_target,
    flags.stale_data_flag,
    CASE WHEN som.training_rate < 0.80 THEN 1 ELSE 0 END
        AS training_support_needed,
    flags.risk_score,
    CASE
        WHEN flags.risk_score >= 4 THEN 'Critical'
        WHEN flags.risk_score = 3 THEN 'High'
        WHEN flags.risk_score = 2 THEN 'Watch'
        ELSE 'Stable'
    END AS risk_band
FROM v_school_operating_metrics AS som
JOIN flags ON som.school_id = flags.school_id;
